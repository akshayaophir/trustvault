from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from tests.helpers import make_user

PASSWORD = "test-password-123"
PDF = b"%PDF-1.4\n%test\n"
client = TestClient(app)

ADMIN_ROUTES = [
    ("get", "/admin/audit"),
    ("get", "/admin/permission-changes"),
    ("get", "/admin/alerts"),
    ("get", "/admin/users"),
    ("get", "/admin/audit/verify"),
]


def login(user):
    r = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def attempt(email, password):
    return client.post("/auth/login", json={"email": email, "password": password}).status_code


@pytest.fixture
def world(db):
    users = {
        "admin": make_user(db, "admin@t.test", "admin"),
        "owner": make_user(db, "owner@t.test", "owner"),
        "reader": make_user(db, "reader@t.test"),
        "stranger": make_user(db, "stranger@t.test"),
    }
    heads = {k: login(u) for k, u in users.items()}
    r = client.post("/documents", headers=heads["owner"], files={"file": ("a.pdf", PDF)})
    assert r.status_code == 201
    doc_id = r.json()["id"]
    client.post(f"/documents/{doc_id}/grants", headers=heads["owner"],
                json={"email": "reader@t.test", "permission": "read"})
    client.get(f"/documents/{doc_id}/download", headers=heads["stranger"])  # a refused attempt
    return SimpleNamespace(users=users, h=heads, doc_id=doc_id)


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
@pytest.mark.parametrize("who", ["owner", "reader", "stranger"])
def test_non_admins_cannot_use_admin_routes(world, who, method, path):
    assert client.request(method, path, headers=world.h[who]).status_code == 403


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_anonymous_cannot_use_admin_routes(world, method, path):
    assert client.request(method, path).status_code == 401


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_admin_can_use_admin_routes(world, method, path):
    assert client.request(method, path, headers=world.h["admin"]).status_code == 200


def test_admin_sees_refused_attempts_and_permission_changes(world):
    h = world.h["admin"]
    rows = client.get("/admin/audit?outcome=denied&action=download", headers=h).json()
    assert [(r["actor"], r["document_id"]) for r in rows] == [("stranger@t.test", world.doc_id)]
    changes = client.get("/admin/permission-changes", headers=h).json()
    assert [(c["action"], c["target"]) for c in changes] == [("grant", "reader@t.test")]


def test_audit_chain_is_intact_then_detects_tampering(world):
    h = world.h["admin"]
    ok = client.get("/admin/audit/verify", headers=h).json()
    assert ok["ok"] is True and ok["checked"] > 3
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_update_delete")
            conn.exec_driver_sql("UPDATE audit_log SET outcome = 'allowed' WHERE outcome = 'denied'")
    finally:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE audit_log ENABLE TRIGGER audit_log_no_update_delete")
    assert client.get("/admin/audit/verify", headers=h).json()["ok"] is False


@pytest.mark.parametrize("sql", ["UPDATE audit_log SET action = 'x'", "DELETE FROM audit_log"])
def test_audit_table_is_append_only(world, sql):
    with pytest.raises(Exception, match="append-only"):
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
    assert client.get("/admin/audit/verify", headers=world.h["admin"]).json()["ok"] is True


def test_deactivating_a_user_ends_their_session_at_once(world):
    reader = world.users["reader"]
    assert client.get("/me", headers=world.h["reader"]).status_code == 200
    r = client.post(f"/admin/users/{reader.id}/deactivate", headers=world.h["admin"])
    assert r.status_code == 200
    assert client.get("/me", headers=world.h["reader"]).status_code == 401
    dl = client.get(f"/documents/{world.doc_id}/download", headers=world.h["reader"])
    assert dl.status_code == 401
    assert attempt(reader.email, PASSWORD) == 401


def test_only_admin_can_deactivate(world):
    r = client.post(f"/admin/users/{world.users['reader'].id}/deactivate",
                    headers=world.h["owner"])
    assert r.status_code == 403


def test_admin_cannot_deactivate_themselves(world):
    r = client.post(f"/admin/users/{world.users['admin'].id}/deactivate",
                    headers=world.h["admin"])
    assert r.status_code == 422


def test_account_locks_after_repeated_failures(world):
    for _ in range(5):
        assert attempt("owner@t.test", "wrong-password-123") == 401
    assert attempt("owner@t.test", PASSWORD) == 429  # even the right password is refused


def test_unknown_email_locks_the_same_way(world):
    for _ in range(5):
        assert attempt("nobody@t.test", "wrong-password-123") == 401
    assert attempt("nobody@t.test", "wrong-password-123") == 429


def test_a_successful_login_resets_the_failure_count(world):
    for _ in range(4):
        assert attempt("owner@t.test", "wrong-password-123") == 401
    assert attempt("owner@t.test", PASSWORD) == 200
    for _ in range(4):
        assert attempt("owner@t.test", "wrong-password-123") == 401
    assert attempt("owner@t.test", PASSWORD) == 200


def test_security_headers_are_set(world):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert "max-age" in r.headers["strict-transport-security"]


def test_home_page_has_a_strict_content_security_policy(world):
    r = client.get("/")
    assert r.status_code == 200
    assert "script-src 'self'" in r.headers["content-security-policy"]