
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import make_user

PASSWORD = "test-password-123"
PDF = b"%PDF-1.4\n%catalogue-test\n"

client = TestClient(app)


def login(user):
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


@pytest.fixture
def world(db):
    users = {
        "owner": make_user(db, "owner@catalogue.test", "owner"),
        "reader": make_user(db, "reader@catalogue.test"),
        "stranger": make_user(db, "stranger@catalogue.test"),
        "admin": make_user(db, "admin@catalogue.test", "admin"),
    }
    headers = {name: login(user) for name, user in users.items()}

    response = client.post(
        "/documents",
        headers=headers["owner"],
        files={"file": ("catalogue-test.pdf", PDF)},
    )
    assert response.status_code == 201

    doc_id = response.json()["id"]

    grant_response = client.post(
        f"/documents/{doc_id}/grants",
        headers=headers["owner"],
        json={"email": "reader@catalogue.test", "permission": "read"},
    )
    assert grant_response.status_code in (200, 201)

    return SimpleNamespace(
        users=users,
        headers=headers,
        doc_id=doc_id,
    )


def test_catalogue_lists_metadata_for_all_active_documents(world):
    response = client.get(
        "/documents/catalogue",
        headers=world.headers["stranger"],
    )

    assert response.status_code == 200
    item = next(
        doc for doc in response.json()
        if doc["id"] == world.doc_id
    )
    assert item["my_permission"] == "none"
    assert item["can_request_access"] is True
    assert "owner_email" in item
    assert "sha256" not in item
    assert "data" not in item


def test_catalogue_shows_owner_permission(world):
    response = client.get(
        "/documents/catalogue",
        headers=world.headers["owner"],
    )

    item = next(
        doc for doc in response.json()
        if doc["id"] == world.doc_id
    )
    assert item["my_permission"] == "owner"
    assert item["can_request_access"] is False


def test_catalogue_shows_granted_reader_permission(world):
    response = client.get(
        "/documents/catalogue",
        headers=world.headers["reader"],
    )

    item = next(
        doc for doc in response.json()
        if doc["id"] == world.doc_id
    )
    assert item["my_permission"] == "read"
    assert item["can_request_access"] is True


def test_admin_catalogue_is_read_only(world):
    response = client.get(
        "/documents/catalogue",
        headers=world.headers["admin"],
    )

    item = next(
        doc for doc in response.json()
        if doc["id"] == world.doc_id
    )
    assert item["my_permission"] == "admin_readonly"
    assert item["can_request_access"] is False


def test_catalogue_search_filters_by_name(world):
    response = client.get(
        "/documents/catalogue",
        params={"q": "catalogue-test"},
        headers=world.headers["stranger"],
    )

    assert response.status_code == 200
    assert any(doc["id"] == world.doc_id for doc in response.json())


def test_catalogue_requires_authentication():
    response = client.get("/documents/catalogue")
    assert response.status_code in (401, 403)
