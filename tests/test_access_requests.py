
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import make_user

PASSWORD = "test-password-123"
PDF = b"%PDF-1.4\n%test\n"
client = TestClient(app)


def login(user):
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def world(db):
    users = {
        "owner": make_user(db, "owner@requests.test", "owner"),
        "requester": make_user(db, "requester@requests.test"),
        "other": make_user(db, "other@requests.test"),
    }
    headers = {name: login(user) for name, user in users.items()}

    response = client.post(
        "/documents",
        headers=headers["owner"],
        files={"file": ("request-test.pdf", PDF)},
    )
    assert response.status_code == 201

    return SimpleNamespace(
        users=users,
        headers=headers,
        doc_id=response.json()["id"],
    )


def test_requester_can_create_read_request(world):
    response = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["requester"],
        json={"permission": "read"},
    )

    assert response.status_code == 201
    assert response.json()["permission"] == "read"
    assert response.json()["status"] == "pending"


def test_duplicate_pending_request_is_rejected(world):
    url = f"/documents/{world.doc_id}/access-requests"
    headers = world.headers["requester"]

    first = client.post(url, headers=headers, json={"permission": "read"})
    second = client.post(url, headers=headers, json={"permission": "edit"})

    assert first.status_code == 201
    assert second.status_code == 409


def test_owner_cannot_request_access_to_own_document(world):
    response = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["owner"],
        json={"permission": "read"},
    )

    assert response.status_code == 409


def test_only_owner_can_list_document_requests(world):
    create = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["requester"],
        json={"permission": "read"},
    )
    assert create.status_code == 201

    denied = client.get(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["other"],
    )
    allowed = client.get(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["owner"],
    )

    assert denied.status_code == 404
    assert allowed.status_code == 200
    assert len(allowed.json()) == 1


def test_requester_can_list_their_own_requests(world):
    created = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["requester"],
        json={"permission": "read"},
    )
    assert created.status_code == 201

    mine = client.get(
        "/access-requests/mine",
        headers=world.headers["requester"],
    )

    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()] == [created.json()["id"]]


def test_non_owner_cannot_approve_request(world):
    created = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["requester"],
        json={"permission": "read"},
    )
    assert created.status_code == 201

    response = client.post(
        f"/access-requests/{created.json()['id']}/decision",
        headers=world.headers["other"],
        json={"decision": "approve"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("decision,expected_status", [
    ("approve", "approved"),
    ("reject", "rejected"),
])
def test_owner_can_decide_request(world, decision, expected_status):
    created = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["requester"],
        json={"permission": "read"},
    )
    assert created.status_code == 201

    response = client.post(
        f"/access-requests/{created.json()['id']}/decision",
        headers=world.headers["owner"],
        json={"decision": decision},
    )

    assert response.status_code == 200
    assert response.json()["status"] == expected_status


def test_approval_grants_requested_read_access(world):
    created = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["requester"],
        json={"permission": "read"},
    )
    assert created.status_code == 201

    decision = client.post(
        f"/access-requests/{created.json()['id']}/decision",
        headers=world.headers["owner"],
        json={"decision": "approve"},
    )
    assert decision.status_code == 200

    download = client.get(
        f"/documents/{world.doc_id}/download",
        headers=world.headers["requester"],
    )
    assert download.status_code == 200


def test_rejection_does_not_grant_access(world):
    created = client.post(
        f"/documents/{world.doc_id}/access-requests",
        headers=world.headers["requester"],
        json={"permission": "read"},
    )
    assert created.status_code == 201

    decision = client.post(
        f"/access-requests/{created.json()['id']}/decision",
        headers=world.headers["owner"],
        json={"decision": "reject"},
    )
    assert decision.status_code == 200

    download = client.get(
        f"/documents/{world.doc_id}/download",
        headers=world.headers["requester"],
    )
    assert download.status_code == 404
