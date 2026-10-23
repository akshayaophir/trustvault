from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuditLog
from tests.helpers import make_user

PASSWORD = "test-password-123"
PDF = b"%PDF-1.4\n%test\n"
client = TestClient(app)


def login(user):
    r = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def grant(headers, doc_id, email, permission="read"):
    return client.post(
        f"/documents/{doc_id}/grants", headers=headers,
        json={"email": email, "permission": permission},
    )


@pytest.fixture
def world(db):
    spec = [("owner", "owner"), ("other", "owner"), ("reader", "viewer"), ("stranger", "viewer")]
    users = {k: make_user(db, f"{k}@t.test", role) for k, role in spec}
    heads = {k: login(u) for k, u in users.items()}
    r = client.post("/documents", headers=heads["owner"], files={"file": ("a.pdf", PDF)})
    assert r.status_code == 201
    return SimpleNamespace(users=users, h=heads, doc_id=r.json()["id"])


def can_download(world, who):
    r = client.get(f"/documents/{world.doc_id}/download", headers=world.h[who])
    return r.status_code == 200


def test_grant_then_revoke_takes_effect_on_the_next_request(world):
    assert not can_download(world, "reader")
    assert grant(world.h["owner"], world.doc_id, "reader@t.test").status_code == 201
    assert can_download(world, "reader")  # same login token as before the grant
    r = client.delete(
        f"/documents/{world.doc_id}/grants/{world.users['reader'].id}",
        headers=world.h["owner"],
    )
    assert r.status_code == 204
    assert not can_download(world, "reader")  # same token, refused at once


def test_regrant_after_revoke_restores_access(world):
    uid = world.users["reader"].id
    grant(world.h["owner"], world.doc_id, "reader@t.test")
    client.delete(f"/documents/{world.doc_id}/grants/{uid}", headers=world.h["owner"])
    assert grant(world.h["owner"], world.doc_id, "reader@t.test").status_code == 201
    assert can_download(world, "reader")


def test_edit_grant_allows_rename_but_read_grant_does_not(world):
    url = f"/documents/{world.doc_id}"
    grant(world.h["owner"], world.doc_id, "reader@t.test", "read")
    assert client.patch(url, headers=world.h["reader"], json={"name": "x.pdf"}).status_code == 404
    grant(world.h["owner"], world.doc_id, "reader@t.test", "edit")
    assert client.patch(url, headers=world.h["reader"], json={"name": "x.pdf"}).status_code == 200


@pytest.mark.parametrize("who", ["other", "reader", "stranger"])
def test_only_the_owner_can_manage_grants(world, who):
    i, sid = world.doc_id, world.users["stranger"].id
    h = world.h[who]
    assert grant(h, i, "stranger@t.test").status_code == 404
    assert client.get(f"/documents/{i}/grants", headers=h).status_code == 404
    assert client.delete(f"/documents/{i}/grants/{sid}", headers=h).status_code == 404
    assert not can_download(world, "stranger")  # nobody got access


def test_a_reader_cannot_share_even_if_they_can_read(world):
    grant(world.h["owner"], world.doc_id, "reader@t.test")
    assert grant(world.h["reader"], world.doc_id, "stranger@t.test").status_code == 404
    assert not can_download(world, "stranger")


def test_anonymous_cannot_manage_grants(world):
    r = client.post(f"/documents/{world.doc_id}/grants",
                    json={"email": "reader@t.test", "permission": "read"})
    assert r.status_code == 401


def test_bad_grant_requests_are_rejected(world):
    h, i = world.h["owner"], world.doc_id
    assert grant(h, i, "nobody@t.test").status_code == 404
    assert grant(h, i, "owner@t.test").status_code == 422        # yourself
    assert grant(h, i, "reader@t.test", "admin").status_code == 422  # invalid level
    extra = client.post(f"/documents/{i}/grants", headers=h,
                        json={"email": "reader@t.test", "permission": "read", "role": "admin"})
    assert extra.status_code == 422


def test_list_shows_only_active_grants(world):
    grant(world.h["owner"], world.doc_id, "reader@t.test")
    grant(world.h["owner"], world.doc_id, "stranger@t.test")
    client.delete(f"/documents/{world.doc_id}/grants/{world.users['stranger'].id}",
                  headers=world.h["owner"])
    rows = client.get(f"/documents/{world.doc_id}/grants", headers=world.h["owner"]).json()
    assert [r["email"] for r in rows] == ["reader@t.test"]


def test_grant_and_revoke_are_audited(db, world):
    grant(world.h["owner"], world.doc_id, "reader@t.test")
    client.delete(f"/documents/{world.doc_id}/grants/{world.users['reader'].id}",
                  headers=world.h["owner"])
    grant(world.h["other"], world.doc_id, "stranger@t.test")  # refused attempt
    rows = db.scalars(
        select(AuditLog).where(AuditLog.action.in_(["grant", "revoke"]))
    ).all()
    seen = {(r.action, r.actor_id, r.outcome) for r in rows}
    assert ("grant", world.users["owner"].id, "allowed") in seen
    assert ("revoke", world.users["owner"].id, "allowed") in seen
    assert ("grant", world.users["other"].id, "denied") in seen
    target = next(r for r in rows if r.action == "grant" and r.outcome == "allowed")
    assert target.target_user_id == world.users["reader"].id