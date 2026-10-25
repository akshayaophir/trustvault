
from datetime import timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.auth import get_current_user
from app.authz import authorize
from app.db import get_db
from app.models import AccessRequest, Document, Grant, User, now

router = APIRouter(tags=["access requests"])


class AccessRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permission: Literal["read", "edit"]


class AccessRequestDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]


def request_view(item: AccessRequest) -> dict:
    return {
        "id": item.id,
        "document_id": item.document_id,
        "requester_id": item.requester_id,
        "permission": item.permission,
        "status": item.status,
        "decided_by": item.decided_by,
        "created_at": item.created_at.isoformat(),
        "decided_at": (
            item.decided_at.isoformat() if item.decided_at else None
        ),
    }


@router.post(
    "/documents/{doc_id}/access-requests",
    status_code=201,
)
def create_access_request(
    doc_id: int,
    body: AccessRequestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, doc_id)

    if doc is None or doc.deleted_at is not None or not user.is_active:
        raise HTTPException(status_code=404, detail="Not found")

    if doc.owner_id == user.id:
        raise HTTPException(
            status_code=409,
            detail="You already own this document",
        )

    existing_grant = db.scalar(
        select(Grant).where(
            Grant.document_id == doc_id,
            Grant.user_id == user.id,
            Grant.revoked_at.is_(None),
        )
    )

    if existing_grant is not None:
        if (
            existing_grant.permission == "edit"
            or existing_grant.permission == body.permission
        ):
            raise HTTPException(
                status_code=409,
                detail="You already have this permission",
            )

    pending = db.scalar(
        select(AccessRequest).where(
            AccessRequest.document_id == doc_id,
            AccessRequest.requester_id == user.id,
            AccessRequest.status == "pending",
        )
    )

    if pending is not None:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending request for this document",
        )

    item = AccessRequest(
        document_id=doc_id,
        requester_id=user.id,
        permission=body.permission,
        status="pending",
    )
    db.add(item)
    db.flush()

    audit.log(
        db,
        user,
        "access_request",
        "allowed",
        document_id=doc_id,
        target_user_id=doc.owner_id,
        detail={"request_id": item.id, "permission": body.permission},
    )
    db.commit()
    db.refresh(item)
    return request_view(item)


@router.get("/access-requests/mine")
def list_my_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(AccessRequest)
        .where(AccessRequest.requester_id == user.id)
        .order_by(AccessRequest.created_at.desc(), AccessRequest.id.desc())
    ).all()
    return [request_view(item) for item in items]


@router.get("/documents/{doc_id}/access-requests")
def list_document_requests(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, doc_id)

    if (
        doc is None
        or doc.deleted_at is not None
        or doc.owner_id != user.id
        or not user.is_active
    ):
        raise HTTPException(status_code=404, detail="Not found")

    items = db.scalars(
        select(AccessRequest)
        .where(AccessRequest.document_id == doc_id)
        .order_by(AccessRequest.created_at.desc(), AccessRequest.id.desc())
    ).all()
    return [request_view(item) for item in items]


@router.post("/access-requests/{request_id}/decision")
def decide_access_request(
    request_id: int,
    body: AccessRequestDecision,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(AccessRequest)
        .where(AccessRequest.id == request_id)
        .with_for_update()
    )

    if item is None or item.status != "pending" or not user.is_active:
        raise HTTPException(status_code=404, detail="Not found")

    doc = db.get(Document, item.document_id)

    if doc is None or doc.deleted_at is not None or doc.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    requester = db.get(User, item.requester_id)
    if requester is None or not requester.is_active:
        raise HTTPException(
            status_code=409,
            detail="The requester is no longer active",
        )

    if body.decision == "approve":
        grant = db.scalar(
            select(Grant)
            .where(
                Grant.document_id == doc.id,
                Grant.user_id == requester.id,
            )
            .with_for_update()
        )

        if grant is None:
            grant = Grant(
                document_id=doc.id,
                user_id=requester.id,
                permission=item.permission,
                granted_by=user.id,
            )
            db.add(grant)
        else:
            # Never downgrade an existing edit grant to read.
            if grant.revoked_at is not None:
                grant.permission = item.permission
            elif grant.permission != "edit":
                grant.permission = item.permission

            grant.granted_by = user.id
            grant.revoked_at = None

        item.status = "approved"
    else:
        item.status = "rejected"

    item.decided_by = user.id
    item.decided_at = now()

    audit.log(
        db,
        user,
        "access_request_decision",
        "allowed",
        document_id=doc.id,
        target_user_id=requester.id,
        detail={
            "request_id": item.id,
            "decision": body.decision,
            "permission": item.permission,
        },
    )

    db.commit()
    db.refresh(item)
    return request_view(item)
