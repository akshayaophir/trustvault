from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import make_user

PASSWORD = "test-password-123"
PDF = b"%PDF-1.4\n%test\n"
client = TestClient(app)


def login(user):
    r = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def world(db):
    users = {
        "owner": make_user(db, "owner@t.test", "owner"),
        "reader": make_user(db, "reader@t.test"),
        "stranger": make_user(db, "stranger@t.test"),
    }
    heads = {k: login(u) for k, u in users.items()}
    ids = {}
    for name, cat in [("salary-letter.pdf", "hr"), ("contract.pdf", "legal")]:
        r = client.post(f"/documents?category={cat}", headers=heads["owner"],
                        files={"file": (name, PDF)})
        assert r.status_code == 201
        ids[name] = r.json()["id"]
    client.post(f"/documents/{ids['contract.pdf']}/grants", headers=heads["owner"],
                json={"email": "reader@t.test", "permission": "read"})
    return SimpleNamespace(h=heads, ids=ids)


def names(resp):
    assert resp.status_code == 200
    return sorted(d["name"] for d in resp.json())


def test_owner_can_search_by_name_category_owner_and_date(world):
    h = world.h["owner"]
    assert names(client.get("/documents?q=salary", headers=h)) == ["salary-letter.pdf"]
    assert names(client.get("/documents?category=legal", headers=h)) == ["contract.pdf"]
    assert len(names(client.get("/documents?owner=owner@t", headers=h))) == 2
    assert len(names(client.get("/documents?created_from=2000-01-01", headers=h))) == 2
    assert names(client.get("/documents?created_to=2000-01-01", headers=h)) == []


def test_stranger_search_never_finds_anything(world):
    h = world.h["stranger"]
    for url in ["/documents", "/documents?q=salary", "/documents?q=contract",
                "/documents?owner=owner", "/documents?category=hr", "/documents?q=%25"]:
        assert client.get(url, headers=h).json() == []


def test_reader_only_finds_the_granted_document(world):
    h = world.h["reader"]
    assert names(client.get("/documents", headers=h)) == ["contract.pdf"]
    assert names(client.get("/documents?q=salary", headers=h)) == []


def test_percent_sign_is_not_a_wildcard(world):
    assert client.get("/documents?q=%25", headers=world.h["owner"]).json() == []


def test_search_requires_login(world):
    assert client.get("/documents?q=salary").status_code == 401