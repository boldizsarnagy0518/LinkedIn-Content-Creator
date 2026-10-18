from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.content.dependencies import get_content_workflow_service
from app.content.repository import SQLiteContentRepository
from app.content.service import ContentWorkflowService
from app.main import app


@pytest.fixture()
def content_client(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    database_path = tmp_path / "contentops-test.db"
    service = ContentWorkflowService(SQLiteContentRepository(database_path))
    app.dependency_overrides[get_content_workflow_service] = lambda: service

    with TestClient(app) as client:
        yield client, database_path

    app.dependency_overrides.clear()


def test_author_memory_http_save_is_shared_with_mcp_and_export(content_client):
    client, path = content_client
    initial = client.get("/writing-profile/memory")
    assert initial.status_code == 200
    payload = {
        "memory": {
            **initial.json(), "background": "Python fejlesztő, saját projektekről írok.",
            "past_posts": [{"title": "Egy tanulság", "body": "Egy saját korábbi poszt szövege.",
                            "topics": "tanulás", "use_as_example": True}],
        },
        "idempotency_key": "http-memory-roundtrip",
    }
    saved = client.put("/writing-profile/memory", json=payload)
    assert saved.status_code == 200
    assert client.put("/writing-profile/memory", json=payload).json() == saved.json()
    assert client.get("/writing-profile/memory").json() == saved.json()
    mcp_repository = SQLiteContentRepository(path)
    context = mcp_repository.get_writing_context(max_examples=5)
    assert context.author_memory.background == payload["memory"]["background"]
    assert context.author_memory.past_posts[0].topics == "tanulás"
    exported = client.get("/content-items/export")
    assert exported.status_code == 200
    assert exported.json()["author_memory"] == saved.json()
    stale = client.put("/writing-profile/memory", json={**payload, "idempotency_key": "http-memory-stale"})
    assert stale.status_code == 409
    assert client.get("/writing-profile/memory").json() == saved.json()


def test_author_memory_rejects_invalid_posts_without_changing_saved_profile(content_client):
    client, _ = content_client
    initial = client.get("/writing-profile/memory").json()
    invalid = {**initial, "past_posts": [{"title": "", "body": "A poszt szövege"}]}
    assert client.put("/writing-profile/memory", json={
        "memory": invalid, "idempotency_key": "invalid-memory-http",
    }).status_code == 422
    assert client.get("/writing-profile/memory").json() == initial


def test_captured_idea_is_visible_through_the_shared_repository(
    content_client: tuple[TestClient, Path],
) -> None:
    client, database_path = content_client

    response = client.post(
        "/content-items/ideas",
        json={
            "raw_idea": "A jó portfólióprojekt valós workflow-problémát old meg.",
            "idempotency_key": "idea-browser-1234",
        },
        headers={"X-Request-ID": "capture-test"},
    )

    assert response.status_code == 201
    assert response.headers["x-request-id"] == "capture-test"
    item = response.json()
    assert item["source_kind"] == "idea"
    assert item["status"] == "captured"
    assert item["raw_input"].startswith("A jó portfólióprojekt")

    list_response = client.get("/content-items", params={"status": "captured", "limit": 5})
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == item["id"]

    # The MCP server creates its own repository instance over this same file.
    independently_loaded = SQLiteContentRepository(database_path).get_content_item(item["id"])
    assert independently_loaded.raw_input == item["raw_input"]


def test_capture_idea_replays_the_same_idempotent_result(content_client: tuple[TestClient, Path]) -> None:
    client, _ = content_client
    payload = {
        "raw_idea": "Write about treating feedback as durable product data.",
        "idempotency_key": "stable-capture-key",
    }

    first = client.post("/content-items/ideas", json=payload)
    replay = client.post("/content-items/ideas", json=payload)

    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]


def test_reusing_capture_key_for_different_input_returns_conflict(
    content_client: tuple[TestClient, Path],
) -> None:
    client, _ = content_client
    client.post(
        "/content-items/ideas",
        json={"raw_idea": "The first idea is long enough.", "idempotency_key": "conflicting-key"},
    )

    response = client.post(
        "/content-items/ideas",
        json={"raw_idea": "A different idea uses the same key.", "idempotency_key": "conflicting-key"},
        headers={"X-Request-ID": "conflict-test"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "content_workflow_conflict"
    assert response.json()["request_id"] == "conflict-test"


def test_getting_unknown_content_item_returns_stable_error(content_client: tuple[TestClient, Path]) -> None:
    client, _ = content_client

    response = client.get("/content-items/missing-item")

    assert response.status_code == 404
    assert response.json()["code"] == "content_item_not_found"


def test_application_api_supports_review_and_profile_workflow(
    content_client: tuple[TestClient, Path],
) -> None:
    client, _ = content_client
    item = client.post(
        "/content-items/ideas",
        json={"raw_idea": "Make review state visible.", "idempotency_key": "api-review-idea"},
    ).json()
    drafted_response = client.post(
        f"/content-items/{item['id']}/versions",
        json={"body": "A concrete reviewed draft.", "idempotency_key": "api-review-draft"},
    )
    assert drafted_response.status_code == 200
    drafted = drafted_response.json()
    version = drafted["versions"][-1]

    feedback_response = client.post(
        f"/content-items/{item['id']}/feedback",
        json={
            "version_id": version["id"],
            "feedback": "Add one example.",
            "idempotency_key": "api-review-feedback",
        },
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json()["status"] == "changes_requested"

    revised_response = client.post(
        f"/content-items/{item['id']}/versions",
        json={
            "body": "A concrete reviewed draft with one real example.",
            "change_summary": "Added the requested example.",
            "idempotency_key": "api-review-revision",
        },
    )
    assert revised_response.status_code == 200
    version = revised_response.json()["versions"][-1]

    approval_response = client.post(
        f"/content-items/{item['id']}/approval",
        json={
            "version_id": version["id"],
            "expected_content_hash": version["content_hash"],
            "idempotency_key": "api-review-approval",
        },
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["active_approval"]["version_id"] == version["id"]

    plan_response = client.put(
        f"/content-items/{item['id']}/publication-plan",
        json={
            "version_id": version["id"],
            "planned_for": "2099-01-01T09:00:00+01:00",
            "timezone": "Europe/Budapest",
            "idempotency_key": "api-publication-plan",
        },
    )
    assert plan_response.status_code == 200
    plan_id = plan_response.json()["publication_plan"]["id"]
    published_response = client.post(
        f"/content-items/{item['id']}/publication-plan/mark-published",
        json={"plan_id": plan_id, "confirmation_note": "Confirmed live.", "idempotency_key": "api-published"},
    )
    assert published_response.status_code == 200

    performance_response = client.post(
        f"/content-items/{item['id']}/performance-snapshots",
        json={"impressions": 500, "reactions": 20, "idempotency_key": "api-performance"},
    )
    assert performance_response.status_code == 200
    assert performance_response.json()["performance_snapshots"][0]["impressions"] == 500

    profile_response = client.put(
        "/writing-profile",
        json={
            "style_instructions": "Short sentences and concrete examples.",
            "target_audience": "Engineering leaders",
            "language": "HU",
            "idempotency_key": "api-writing-profile",
        },
    )
    assert profile_response.status_code == 200
    assert client.get("/writing-profile").json()["language"] == "hu"
