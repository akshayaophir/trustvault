
import hashlib
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import audit
from app.auth import get_current_user, require_role
from app.authz import authorize
from app.db import get_db
from app.models import Document, DocumentBlob, Grant, User, now
from app.uploads import MAX_BYTES, UploadError, clean_name, validate_upload

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentPatch(BaseModel):
    model_config = {"extra": "forbid"}
    name: str | None = Field(default=None, min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)


def view(doc: Document) -> dict:
    return {
        "id": doc.id,
        "name": doc.name,
        "category": doc.category,
        "mime": doc.mime,
        "size": doc.size,
        "owner_id": doc.owner_id,
        "created_at": doc.created_at.isoformat(),
    }


def like(text: str) -> str:
    """Make user text safe for LIKE: backslash, % and _ are plain characters."""
    for ch in ("\\", "%", "_"):
        text = text.replace(ch, "\\" + ch)
    return f"%{text}%"


def visible_documents(user: User):
    """Return the user's own documents and actively granted documents."""
    return (
        select(Document, Grant.permission)
        .outerjoin(
            Grant,
            and_(
                Grant.document_id == Document.id,
                Grant.user_id == user.id,
                Grant.revoked_at.is_(None),
            ),
        )
        .where(Document.deleted_at.is_(None))
        .where(or_(Document.owner_id == user.id, Grant.id.is_not(None)))
    )


@router.post("", status_code=201)
async def upload(
    category: str | None = Query(default=None, max_length=100),
    file: UploadFile = File(...),
    user: User = Depends(require_role("owner")),
    db: Session = Depends(get_db),
):
    data = await file.read(MAX_BYTES + 1)

    try:
        name, mime = validate_upload(file.filename or "", data)
    except UploadError as e:
        audit.log(
            db,
            user,
            "upload",
            "denied",
            detail={"reason": e.message},
        )
        db.commit()
        raise HTTPException(status_code=e.status, detail=e.message)

    doc = Document(
        owner_id=user.id,
        name=name,
        category=category or None,
        mime=mime,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )

    db.add(doc)
    db.flush()

    db.add(DocumentBlob(document_id=doc.id, data=data))

    audit.log(
        db,
        user,
        "upload",
        "allowed",
        document_id=doc.id,
        detail={"name": name, "size": len(data)},
    )

    # Save document, content, and audit entry together.
    db.commit()
    db.refresh(doc)

    return view(doc)


@router.get("")
def list_documents(
    q: str | None = Query(default=None, max_length=100),
    owner: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=100),
    created_from: date | None = None,
    created_to: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Apply permission filtering before other search filters.
    stmt = visible_documents(user)

    if q:
        stmt = stmt.where(
            Document.name.ilike(like(q), escape="\\")
        )

    if category:
        stmt = stmt.where(
            Document.category.ilike(like(category), escape="\\")
        )

    if owner:
        stmt = stmt.where(
            Document.owner_id.in_(
                select(User.id).where(
                    User.email.ilike(like(owner), escape="\\")
                )
            )
        )

    if created_from:
        start = datetime.combine(
            created_from,
            time.min,
            tzinfo=timezone.utc,
        )
        stmt = stmt.where(Document.created_at >= start)

    if created_to:
        end = datetime.combine(
            created_to + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        stmt = stmt.where(Document.created_at < end)

    rows = db.execute(
        stmt.order_by(Document.created_at.desc())
    ).all()

    emails = {}

    if rows:
        emails = dict(
            db.execute(
                select(User.id, User.email).where(
                    User.id.in_({doc.owner_id for doc, _ in rows})
                )
            ).all()
        )

    return [
        {
            **view(doc),
            "owner_email": emails.get(doc.owner_id),
            "my_permission": (
                "owner" if doc.owner_id == user.id else permission
            ),
        }
        for doc, permission in rows
    ]


@router.get("/{doc_id}")
def get_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = authorize(db, user, doc_id, "read", label="view")

    audit.log(
        db,
        user,
        "view",
        "allowed",
        document_id=doc.id,
    )

    db.commit()
    return view(doc)


@router.get("/{doc_id}/download")
def download(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = authorize(db, user, doc_id, "read", label="download")

    blob = db.scalar(
        select(DocumentBlob).where(
            DocumentBlob.document_id == doc.id
        )
    )

    if blob is None:
        raise HTTPException(status_code=404, detail="Not found")

    audit.log(
        db,
        user,
        "download",
        "allowed",
        document_id=doc.id,
        detail={"name": doc.name},
    )

    db.commit()

    return Response(
        content=blob.data,
        media_type=doc.mime,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.name}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


@router.patch("/{doc_id}")
def update_document(
    doc_id: int,
    body: DocumentPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = authorize(db, user, doc_id, "edit", label="update")
    changes = {}

    if body.name is not None:
        name = clean_name(body.name)

        if not name:
            raise HTTPException(
                status_code=422,
                detail="Invalid name",
            )

        # A document's file extension cannot be changed.
        if (
            name.rsplit(".", 1)[-1].lower()
            != doc.name.rsplit(".", 1)[-1].lower()
        ):
            raise HTTPException(
                status_code=422,
                detail="The file type cannot be changed",
            )

        doc.name = name
        changes["name"] = name

    if body.category is not None:
        doc.category = body.category or None
        changes["category"] = doc.category

    audit.log(
        db,
        user,
        "update",
        "allowed",
        document_id=doc.id,
        detail=changes,
    )

    db.commit()
    db.refresh(doc)

    return view(doc)


@router.put("/{doc_id}/content")
async def replace_content(
    doc_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = authorize(db, user, doc_id, "edit", label="replace")

    data = await file.read(MAX_BYTES + 1)

    try:
        # Validate replacement content against the existing file name.
        validate_upload(doc.name, data)

    except UploadError as e:
        audit.log(
            db,
            user,
            "replace",
            "denied",
            document_id=doc.id,
            detail={"reason": e.message},
        )

        db.commit()

        raise HTTPException(
            status_code=e.status,
            detail=e.message,
        )

    blob = db.scalar(
        select(DocumentBlob).where(
            DocumentBlob.document_id == doc.id
        )
    )

    if blob is None:
        raise HTTPException(status_code=404, detail="Not found")

    blob.data = data
    doc.size = len(data)
    doc.sha256 = hashlib.sha256(data).hexdigest()

    audit.log(
        db,
        user,
        "replace",
        "allowed",
        document_id=doc.id,
        detail={
            "name": doc.name,
            "size": len(data),
            "sha256": doc.sha256,
        },
    )

    db.commit()
    db.refresh(doc)

    return view(doc)


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = authorize(db, user, doc_id, "delete")

    # Soft delete: preserve the document record and audit history.
    doc.deleted_at = now()

    audit.log(
        db,
        user,
        "delete",
        "allowed",
        document_id=doc.id,
    )

    db.commit()

    return Response(status_code=204)
