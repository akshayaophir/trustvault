from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.authz import authorize
from app.models import AuditLog, Grant, now
from tests.helpers import make_doc, make_grant, make_user

ACTIONS = ["read", "edit", "delete", "share"]

ALLOWED = [
    ("owner", "read"), ("owner", "edit"), ("owner", "delete"), ("owner", "share"),
    ("reader", "read"),
    ("editor", "read"), ("editor", "edit"),
]

DENIED = (
    [(who, a) for who in ("stranger", "other_owner", "admin", "revoked") for a in ACTIONS]
    + [("reader", "edit"), ("reader", "delete"), ("reader", "share")]
    + [("editor", "delete"), ("editor", "share")]
)


@pytest.fixture
def world(db):
    owner = make_user(db, "owner@t.test", "owner")
    w = SimpleNamespace(
        owner=owner,
        other_owner=make_user(db, "other@t.test", "owner"),
        reader=make_user(db, "reader@t.test"),
        editor=make_user(db, "editor@t.test"),
        revoked=make_user(db, "revoked@t.test"),
        stranger=make_user(db, "stranger@t.test"),
        admin=make_user(db, "admin@t.test", "admin"),
    )
    w.doc = make_doc(db, owner)
    make_grant(db, w.doc, w.reader, "read", owner)
    make_grant(db, w.doc, w.editor, "edit", owner)
    make_grant(db, w.doc, w.revoked, "read", owner, revoked=True)
    return w


@pytest.mark.parametrize("who,action", ALLOWED)
def test_allowed(db, world, who, action):
    doc = authorize(db, getattr(world, who), world.doc.id, action)
    assert doc.id == world.doc.id


@pytest.mark.parametrize("who,action", DENIED)
def test_denied_is_404(db, world, who, action):
    with pytest.raises(HTTPException) as exc:
        authorize(db, getattr(world, who), world.doc.id, action)
    assert exc.value.status_code == 404


def test_revoking_takes_effect_immediately(db, world):
    authorize(db, world.reader, world.doc.id, "read")  # works now
    grant = db.scalar(select(Grant).where(Grant.user_id == world.reader.id))
    grant.revoked_at = now()
    db.commit()
    with pytest.raises(HTTPException):
        authorize(db, world.reader, world.doc.id, "read")  # refused at once


def test_denied_attempt_is_audited(db, world):
    with pytest.raises(HTTPException):
        authorize(db, world.stranger, world.doc.id, "read")
    row = db.scalars(select(AuditLog)).one()
    assert (row.actor_id, row.action, row.outcome, row.document_id) == (
        world.stranger.id, "read", "denied", world.doc.id,
    )


def test_missing_document_is_404(db, world):
    with pytest.raises(HTTPException) as exc:
        authorize(db, world.owner, 999999, "read")
    assert exc.value.status_code == 404


def test_deleted_document_is_denied_even_for_owner(db, world):
    world.doc.deleted_at = now()
    db.commit()
    with pytest.raises(HTTPException):
        authorize(db, world.owner, world.doc.id, "read")


def test_inactive_user_is_denied(db, world):
    world.owner.is_active = False
    db.commit()
    with pytest.raises(HTTPException):
        authorize(db, world.owner, world.doc.id, "read")


def test_unknown_action_is_denied_even_for_owner(db, world):
    with pytest.raises(HTTPException):
        authorize(db, world.owner, world.doc.id, "teleport")