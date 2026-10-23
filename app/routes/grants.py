from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.auth import get_current_user
from app.authz import authorize
from app.db import get_db
from app.models import Grant, User, now

router = APIRouter(prefix="/documents/{doc_id}/grants", tags=["grants"])


class GrantIn(BaseModel):
    model_config = {"extra": "forbid"}  # unknown fields are rejected
    email: str
    permission: Literal["read", "edit"]


@router.post("", status_code=201)
def grant_access(
    doc_id: int,
    body: GrantIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only the owner may share. A stranger gets the same 404 as for a missing document.
    doc = authorize(db, user, doc_id, "share", label="grant")
    target = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=422, detail="You already own this document")

    grant = db.scalar(
        select(Grant).where(Grant.document_id == doc.id, Grant.user_id == target.id)
    )
    if grant is None:
        grant = Grant(
            document_id=doc.id,
            user_id=target.id,
            permission=body.permission,
            granted_by=user.id,
        )
        db.add(grant)
    else:  # a returning user: update the old row and make it active again
        grant.permission = body.permission
        grant.granted_by = user.id
        grant.revoked_at = None

    audit.log(
        db, user, "grant", "allowed",
        document_id=doc.id, target_user_id=target.id,
        detail={"permission": body.permission},
    )
    db.commit()
    return {"document_id": doc.id, "user_id": target.id, "permission": body.permission}


@router.get("")
def list_grants(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = authorize(db, user, doc_id, "share", label="list_grants")
    rows = db.execute(
        select(Grant, User.email)
        .join(User, User.id == Grant.user_id)
        .where(Grant.document_id == doc.id, Grant.revoked_at.is_(None))
    ).all()
    return [
        {
            "user_id": g.user_id,
            "email": email,
            "permission": g.permission,
            "granted_at": g.created_at.isoformat(),
        }
        for g, email in rows
    ]


@router.delete("/{user_id}", status_code=204)
def revoke_access(
    doc_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = authorize(db, user, doc_id, "share", label="revoke")
    grant = db.scalar(
        select(Grant).where(
            Grant.document_id == doc.id,
            Grant.user_id == user_id,
            Grant.revoked_at.is_(None),
        )
    )
    if grant is None:
        raise HTTPException(status_code=404, detail="No active grant for that user")
    grant.revoked_at = now()  # never deleted: the history stays
    audit.log(db, user, "revoke", "allowed", document_id=doc.id, target_user_id=user_id)
    db.commit()
    return Response(status_code=204)