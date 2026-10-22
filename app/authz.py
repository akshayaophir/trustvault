from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.models import Document, Grant, User

KNOWN_ACTIONS = {"read", "edit", "delete", "share"}
OWNER_ONLY = {"delete", "share"}  # actions only the owner may do
ALLOWED_PERMISSIONS = {
    "read": {"read", "edit"},  # which grant types allow this action
    "edit": {"edit"},
}


def is_allowed(db: Session, user: User, doc: Document | None, action: str) -> bool:
    """Pure yes/no decision. Denies by default."""
    if action not in KNOWN_ACTIONS:
        return False
    if doc is None or doc.deleted_at is not None or not user.is_active:
        return False
    if doc.owner_id == user.id:
        return True
    if action in OWNER_ONLY or action not in ALLOWED_PERMISSIONS:
        return False
    grant = db.scalar(
        select(Grant).where(
            Grant.document_id == doc.id,
            Grant.user_id == user.id,
            Grant.revoked_at.is_(None),
        )
    )
    return grant is not None and grant.permission in ALLOWED_PERMISSIONS[action]


def authorize(db: Session, user: User, doc_id: int, action: str) -> Document:
    """The ONLY place that decides document access. Every document route calls it."""
    doc = db.get(Document, doc_id)
    if not is_allowed(db, user, doc, action):
        audit.log(db, user, action, "denied", document_id=doc_id)
        db.commit()  # keep the record of the refused attempt
        raise HTTPException(status_code=404, detail="Not found")
    return doc