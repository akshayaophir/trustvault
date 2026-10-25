
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.models import Document, Grant, User

KNOWN_ACTIONS = {"read", "edit", "delete", "share"}
OWNER_ONLY = {"delete", "share"}  # Actions only the owner may do

ALLOWED_PERMISSIONS = {
    "read": {"read", "edit"},  # Grant types that allow reading
    "edit": {"edit"},
}


def is_allowed(db: Session, user: User, doc: Document | None, action: str) -> bool:
    """Pure yes/no authorization decision. Denies by default."""

    if action not in KNOWN_ACTIONS:
        return False

    if doc is None or doc.deleted_at is not None or not user.is_active:
        return False

    # Owners retain full control over their own active documents.
    if doc.owner_id == user.id:
        return True

    # Admins may read/download active documents only.
    # They cannot edit, delete, or share documents by default.
    if user.role == "admin":
        return action == "read"

    # Only owners can delete or share documents.
    if action in OWNER_ONLY or action not in ALLOWED_PERMISSIONS:
        return False

    # Other users need an active grant with sufficient permission.
    grant = db.scalar(
        select(Grant).where(
            Grant.document_id == doc.id,
            Grant.user_id == user.id,
            Grant.revoked_at.is_(None),
        )
    )

    return grant is not None and grant.permission in ALLOWED_PERMISSIONS[action]


def authorize(
    db: Session,
    user: User,
    doc_id: int,
    action: str,
    label: str | None = None,
) -> Document:
    """The central authorization check for document access."""

    doc = db.get(Document, doc_id)

    if not is_allowed(db, user, doc, action):
        # Record denied access attempts for auditing.
        audit.log(
            db,
            user,
            label or action,
            "denied",
            document_id=doc_id,
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Not found")

    return doc
