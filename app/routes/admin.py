from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import audit
from app.audit import verify_chain
from app.auth import require_role
from app.db import get_db
from app.models import AuditLog, User, now

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role("admin")  # 401 if not signed in, 403 if not an admin

PERMISSION_ACTIONS = ["grant", "revoke", "deactivate_user", "activate_user"]


def emails_for(db: Session, ids) -> dict:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    return dict(db.execute(select(User.id, User.email).where(User.id.in_(ids))).all())


def rows_out(db: Session, rows) -> list[dict]:
    emails = emails_for(db, [r.actor_id for r in rows] + [r.target_user_id for r in rows])
    return [
        {
            "id": r.id, "time": r.ts.isoformat(),
            "actor_id": r.actor_id, "actor": emails.get(r.actor_id),
            "action": r.action, "outcome": r.outcome,
            "document_id": r.document_id,
            "target_user_id": r.target_user_id, "target": emails.get(r.target_user_id),
            "detail": r.detail,
        }
        for r in rows
    ]


@router.get("/audit")
def activity(
    action: str | None = Query(default=None, max_length=50),
    outcome: Literal["allowed", "denied"] | None = None,
    actor_id: int | None = None,
    document_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if document_id is not None:
        stmt = stmt.where(AuditLog.document_id == document_id)
    rows = db.scalars(stmt.order_by(AuditLog.id.desc()).limit(limit).offset(offset)).all()
    return rows_out(db, rows)


@router.get("/permission-changes")
def permission_changes(
    limit: int = Query(default=100, ge=1, le=500),
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    stmt = (
        select(AuditLog)
        .where(AuditLog.action.in_(PERMISSION_ACTIONS))
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    return rows_out(db, db.scalars(stmt).all())


@router.get("/audit/verify")
def verify(admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return verify_chain(db)


@router.get("/alerts")
def alerts(admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    found = []
    hour_ago = now() - timedelta(hours=1)

    refused = db.execute(
        select(AuditLog.actor_id, func.count())
        .where(AuditLog.outcome == "denied", AuditLog.ts > hour_ago,
               AuditLog.actor_id.is_not(None))
        .group_by(AuditLog.actor_id)
        .having(func.count() >= 5)
    ).all()
    emails = emails_for(db, [a for a, _ in refused])
    for actor_id, n in refused:
        found.append({"kind": "many_refused_requests", "actor": emails.get(actor_id),
                      "count": n, "window": "1 hour"})

    unknown = db.scalar(
        select(func.count()).select_from(AuditLog)
        .where(AuditLog.action == "login", AuditLog.outcome == "denied",
               AuditLog.actor_id.is_(None), AuditLog.ts > hour_ago)
    ) or 0
    if unknown >= 10:
        found.append({"kind": "failed_logins_for_unknown_accounts", "actor": None,
                      "count": unknown, "window": "1 hour"})

    ten_min_ago = now() - timedelta(minutes=10)
    bulk = db.execute(
        select(AuditLog.actor_id, func.count())
        .where(AuditLog.action == "download", AuditLog.outcome == "allowed",
               AuditLog.ts > ten_min_ago)
        .group_by(AuditLog.actor_id)
        .having(func.count() >= 10)
    ).all()
    emails = emails_for(db, [a for a, _ in bulk])
    for actor_id, n in bulk:
        found.append({"kind": "bulk_downloads", "actor": emails.get(actor_id),
                      "count": n, "window": "10 minutes"})
    return found


@router.get("/users")
def users(admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).order_by(User.id)).all()
    return [{"id": u.id, "email": u.email, "role": u.role, "is_active": u.is_active}
            for u in rows]


def set_active(db: Session, admin: User, user_id: int, active: bool) -> dict:
    if user_id == admin.id:
        raise HTTPException(status_code=422, detail="You cannot change your own account")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = active
    if not active:
        target.token_version += 1  # every token issued to them stops working
    audit.log(db, admin, "activate_user" if active else "deactivate_user", "allowed",
              target_user_id=target.id)
    db.commit()
    return {"id": target.id, "is_active": active}


@router.post("/users/{user_id}/deactivate")
def deactivate(user_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return set_active(db, admin, user_id, False)


@router.post("/users/{user_id}/activate")
def activate(user_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    return set_active(db, admin, user_id, True)