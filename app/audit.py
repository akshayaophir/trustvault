import hashlib
import json
from datetime import timezone

from sqlalchemy import select, text

from app.models import AuditLog, User, now


def compute_hash(prev_hash, ts, actor_id, action, document_id, target_user_id, outcome, detail):
    payload = json.dumps(
        [prev_hash or "", ts.astimezone(timezone.utc).isoformat(), actor_id, action,
         document_id, target_user_id, outcome, detail],
        sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log(db, actor: User | None, action: str, outcome: str,
        document_id: int | None = None, target_user_id: int | None = None,
        detail: dict | None = None):
    """Add one audit row, chained to the previous row. The caller commits."""
    # One writer at a time, so the chain has a single order.
    db.execute(text("SELECT pg_advisory_xact_lock(727001)"))
    prev = db.scalar(select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1))
    ts = now()
    actor_id = actor.id if actor else None
    entry = AuditLog(
        ts=ts, actor_id=actor_id, action=action, outcome=outcome,
        document_id=document_id, target_user_id=target_user_id, detail=detail,
        prev_hash=prev,
        hash=compute_hash(prev, ts, actor_id, action, document_id, target_user_id, outcome, detail),
    )
    db.add(entry)
    db.flush()
    return entry


def verify_chain(db) -> dict:
    prev = None
    checked = 0
    for row in db.scalars(select(AuditLog).order_by(AuditLog.id)).all():
        expected = compute_hash(prev, row.ts, row.actor_id, row.action, row.document_id,
                                row.target_user_id, row.outcome, row.detail)
        if row.prev_hash != prev or row.hash != expected:
            return {"ok": False, "checked": checked, "first_bad_id": row.id}
        prev = row.hash
        checked += 1
    return {"ok": True, "checked": checked, "head": prev}