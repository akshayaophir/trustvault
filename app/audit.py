from app.models import AuditLog, User


def log(
    db,
    actor: User | None,
    action: str,
    outcome: str,
    document_id: int | None = None,
    target_user_id: int | None = None,
    detail: dict | None = None,
):
    """Add an audit row to the current transaction. The caller commits."""
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        outcome=outcome,
        document_id=document_id,
        target_user_id=target_user_id,
        detail=detail,
        hash="pending",  # replaced by a real hash chain on Day 3
    )
    db.add(entry)
    return entry