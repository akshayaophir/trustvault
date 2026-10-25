from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuditLog
from tests.helpers import make_user

PASSWORD = "test-password-123"
PDF_V1 = b"%PDF-1.4\n%version one\n"
PDF_V2 = b"%PDF-1.4\n%version two, edited\n"
client = TestClient(app)


def login(user):
    r = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def put(headers, doc_id, data=PDF_V2):
    return client.put(f"/documents/{doc_id}/content", headers=headers, files={"file": ("x.pdf", data)})


@pytest.fixture
def world(db):
    spec = [("owner", "owner"), ("other", "owner"), ("editor", "viewer"),
            ("reader", "viewer"), ("stranger", "viewer"), ("admin", "admin")]
    users = {k: make_user(db, f"{k}@t.test", role) for k, role in spec}
    heads = {k: login(u) for k, u in users.items()}
    r = client.post("/documents", headers=heads["owner"], files={"file": ("a.pdf", PDF_V1)})
    assert r.status_code == 201
    doc_id = r.json()["id"]
    for who, level in [("editor", "edit"), ("reader", "read")]:
        client.post(f"/documents/{doc_id}/grants", headers=heads["owner"],
                    json={"email": f"{who}@t.test", "permission": level})
    return SimpleNamespace(users=users, h=heads, doc_id=doc_id)


def content(world, who):
    return client.get(f"/documents/{world.doc_id}/download", headers=world.h[who]).content


def test_owner_and_editor_can_replace_the_content(world):
    assert put(world.h["owner"], world.doc_id).status_code == 200
    assert content(world, "reader") == PDF_V2
    assert put(world.h["editor"], world.doc_id, PDF_V1).status_code == 200
    assert content(world, "owner") == PDF_V1


@pytest.mark.parametrize("who", ["reader", "stranger", "other", "admin"])
def test_others_cannot_replace_the_content(world, who):
    assert put(world.h[who], world.doc_id).status_code == 404
    assert content(world, "owner") == PDF_V1


def test_anonymous_cannot_replace_the_content(world):
    r = client.put(f"/documents/{world.doc_id}/content", files={"file": ("x.pdf", PDF_V2)})
    assert r.status_code == 401


@pytest.mark.parametrize("data", [b"<html><script>alert(1)</script></html>", b"", b"plain text pretending"])
def test_replacement_must_be_the_same_kind_of_file(world, data):
    assert put(world.h["owner"], world.doc_id, data).status_code == 400
    assert content(world, "owner") == PDF_V1


def test_oversized_replacement_is_rejected(world):
    big = b"%PDF-" + b"0" * (5 * 1024 * 1024)
    assert put(world.h["owner"], world.doc_id, big).status_code == 413


def test_replacement_is_audited_allowed_and_denied(db, world):
    put(world.h["editor"], world.doc_id)
    put(world.h["reader"], world.doc_id)
    rows = db.scalars(select(AuditLog).where(AuditLog.action == "replace")).all()
    assert {(r.actor_id, r.outcome) for r in rows} == {
        (world.users["editor"].id, "allowed"),
        (world.users["reader"].id, "denied"),
    }


def test_rename_cannot_change_the_file_type(world):
    r = client.patch(f"/documents/{world.doc_id}", headers=world.h["owner"], json={"name": "notes.txt"})
    assert r.status_code == 422