from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuditLog, Document, Grant, now
from tests.helpers import make_grant, make_user

PASSWORD = "test-password-123"  # the password tests/helpers.py gives every test user
PDF = b"%PDF-1.4\n%test file\n"
client = TestClient(app)


def login(user):
    r = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def upload(headers, name="secret.pdf", data=PDF):
    return client.post("/documents", headers=headers, files={"file": (name, data)})


@pytest.fixture
def world(db):
    users = {
        "owner": make_user(db, "owner@t.test", "owner"),
        "other": make_user(db, "other@t.test", "owner"),
        "reader": make_user(db, "reader@t.test"),
        "editor": make_user(db, "editor@t.test"),
        "stranger": make_user(db, "stranger@t.test"),
        "admin": make_user(db, "admin@t.test", "admin"),
    }
    heads = {k: login(u) for k, u in users.items()}
    r = upload(heads["owner"])
    assert r.status_code == 201
    doc = db.get(Document, r.json()["id"])
    make_grant(db, doc, users["reader"], "read", users["owner"])
    make_grant(db, doc, users["editor"], "edit", users["owner"])
    return SimpleNamespace(users=users, h=heads, doc=doc)


ROUTES = [
    ("get", "/documents/{id}", None),
    ("get", "/documents/{id}/download", None),
    ("patch", "/documents/{id}", {"name": "x.pdf"}),
    ("delete", "/documents/{id}", None),
]


@pytest.mark.parametrize("who", ["stranger", "other", "admin"])
@pytest.mark.parametrize("method,path,body", ROUTES)
def test_user_without_grant_gets_404(world, who, method, path, body):
    r = client.request(method, path.format(id=world.doc.id), headers=world.h[who], json=body)
    assert r.status_code == 404


@pytest.mark.parametrize("method,path,body", ROUTES)
def test_anonymous_gets_401(world, method, path, body):
    r = client.request(method, path.format(id=world.doc.id), json=body)
    assert r.status_code == 401


def test_reader_can_download_but_not_change(world):
    h, i = world.h["reader"], world.doc.id
    assert client.get(f"/documents/{i}/download", headers=h).content == PDF
    assert client.patch(f"/documents/{i}", headers=h, json={"name": "x.pdf"}).status_code == 404
    assert client.delete(f"/documents/{i}", headers=h).status_code == 404


def test_editor_can_rename_but_not_delete(world):
    h, i = world.h["editor"], world.doc.id
    assert client.patch(f"/documents/{i}", headers=h, json={"name": "new.pdf"}).status_code == 200
    assert client.delete(f"/documents/{i}", headers=h).status_code == 404


def test_owner_can_delete_and_it_disappears(world):
    h, i = world.h["owner"], world.doc.id
    assert client.delete(f"/documents/{i}", headers=h).status_code == 204
    assert client.get(f"/documents/{i}", headers=h).status_code == 404


def test_revoked_grant_stops_download_at_once(db, world):
    i = world.doc.id
    assert client.get(f"/documents/{i}/download", headers=world.h["reader"]).status_code == 200
    grant = db.scalar(select(Grant).where(Grant.user_id == world.users["reader"].id))
    grant.revoked_at = now()
    db.commit()
    assert client.get(f"/documents/{i}/download", headers=world.h["reader"]).status_code == 404


def test_list_only_shows_visible_documents(world):
    assert client.get("/documents", headers=world.h["stranger"]).json() == []
    assert client.get("/documents", headers=world.h["admin"]).json() == []
    reader = client.get("/documents", headers=world.h["reader"]).json()
    assert [d["my_permission"] for d in reader] == ["read"]
    owner = client.get("/documents", headers=world.h["owner"]).json()
    assert [d["my_permission"] for d in owner] == ["owner"]


def test_viewer_cannot_upload(world):
    assert upload(world.h["reader"]).status_code == 403


def test_extra_fields_are_rejected(world):
    r = client.patch(f"/documents/{world.doc.id}", headers=world.h["owner"],
                     json={"name": "x.pdf", "owner_id": 999})
    assert r.status_code == 422


@pytest.mark.parametrize("name,data", [
    ("virus.exe", b"MZ\x90\x00"),
    ("fake.pdf", b"<html><script>alert(1)</script></html>"),
    ("page.html", b"<html></html>"),
    ("empty.pdf", b""),
    ("../../etc/passwd.pdf", b"not a pdf"),
    ("noext", PDF),
])
def test_bad_uploads_are_rejected(world, name, data):
    assert upload(world.h["owner"], name, data).status_code == 400


def test_oversized_upload_is_rejected(world):
    big = b"%PDF-" + b"0" * (5 * 1024 * 1024)
    assert upload(world.h["owner"], "big.pdf", big).status_code == 413


def test_filename_is_sanitised(world):
    r = upload(world.h["owner"], "../../evil name.pdf")
    assert r.status_code == 201
    assert r.json()["name"] == "evil name.pdf"


def test_download_has_safe_headers(world):
    r = client.get(f"/documents/{world.doc.id}/download", headers=world.h["owner"])
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-disposition"].startswith("attachment")


def test_download_is_audited_allowed_and_denied(db, world):
    i = world.doc.id
    client.get(f"/documents/{i}/download", headers=world.h["owner"])
    client.get(f"/documents/{i}/download", headers=world.h["stranger"])
    rows = db.scalars(select(AuditLog).where(AuditLog.action == "download")).all()
    assert {(r.actor_id, r.outcome) for r in rows} == {
        (world.users["owner"].id, "allowed"),
        (world.users["stranger"].id, "denied"),
    }