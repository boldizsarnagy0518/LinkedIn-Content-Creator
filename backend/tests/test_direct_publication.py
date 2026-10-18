import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.content.models import PublicationPlanStatus
from app.content.repository import ConflictError, SQLiteContentRepository, WorkflowError
from app.content.service import ContentWorkflowService

POST_URL = "https://www.linkedin.com/feed/update/urn:li:activity:7300000000000000000/"


def make_service(database_path: Path) -> ContentWorkflowService:
    return ContentWorkflowService(SQLiteContentRepository(database_path))


def approved_item(service: ContentWorkflowService, suffix: str) -> tuple[str, str]:
    item = service.capture_idea("Posted right away.", f"idea-direct-{suffix}")
    version = service.save_draft_version(item.id, "Approved copy", f"draft-direct-{suffix}").versions[-1]
    service.approve_draft(item.id, version.id, version.content_hash, f"approve-direct-{suffix}")
    return item.id, version.id


def test_direct_publication_records_the_confirmed_fact_without_a_plan(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item_id, version_id = approved_item(service, "001")
    published_at = datetime.now(UTC) - timedelta(hours=2)

    published = service.record_direct_publication(
        item_id,
        version_id,
        "Europe/Budapest",
        "direct-publish-001",
        published_at=published_at,
        post_url=POST_URL,
        confirmation_note="Posted from my phone.",
    )

    plan = published.publication_plan
    assert plan is not None
    assert plan.status is PublicationPlanStatus.PUBLISHED
    assert plan.version_id == version_id
    assert plan.published_at == published_at
    assert plan.post_url == POST_URL
    assert plan.external_confirmation_note == "Posted from my phone."
    assert published.events[0].event_type == "publication_confirmed"
    assert published.events[0].details["direct"] is True

    retried = service.record_direct_publication(
        item_id,
        version_id,
        "Europe/Budapest",
        "direct-publish-001",
        published_at=published_at,
        post_url=POST_URL,
        confirmation_note="Posted from my phone.",
    )
    assert retried == published

    measured = service.record_performance_snapshot(item_id, "direct-metrics-001", impressions=310)
    assert measured.performance_snapshots[0].publication_plan_id == plan.id

    with pytest.raises(ConflictError, match="already recorded as published"):
        service.record_direct_publication(item_id, version_id, "Europe/Budapest", "direct-publish-002")


def test_direct_publication_requires_the_current_approved_version(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item = service.capture_idea("Not approved yet.", "idea-direct-unapproved")
    version = service.save_draft_version(item.id, "Draft only", "draft-direct-unapproved").versions[-1]

    with pytest.raises(ConflictError, match="currently approved"):
        service.record_direct_publication(item.id, version.id, "Europe/Budapest", "direct-unapproved")

    item_id, first_version_id = approved_item(service, "stale")
    service.save_draft_version(item_id, "Edited after approval", "draft-direct-stale-2")
    with pytest.raises(ConflictError, match="currently approved"):
        service.record_direct_publication(item_id, first_version_id, "Europe/Budapest", "direct-stale")


def test_direct_publication_replaces_an_unconfirmed_plan(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item_id, version_id = approved_item(service, "planned")
    planned = service.set_publication_plan(
        item_id, version_id, datetime.now(UTC) + timedelta(days=1), "Europe/Budapest", "plan-direct-001"
    )
    assert planned.publication_plan is not None

    published = service.record_direct_publication(item_id, version_id, "Europe/Budapest", "direct-planned")
    assert published.publication_plan is not None
    assert published.publication_plan.id == planned.publication_plan.id
    assert published.publication_plan.status is PublicationPlanStatus.PUBLISHED
    assert published.publication_plan.published_at is not None


@pytest.mark.parametrize(
    "post_url",
    [
        "http://www.linkedin.com/feed/update/urn:li:activity:1/",
        "https://linkedin.com.evil.example/feed/",
        "https://user:secret@www.linkedin.com/feed/",
        "https://example.com/post",
    ],
)
def test_post_url_must_be_a_linkedin_https_link(tmp_path: Path, post_url: str) -> None:
    service = make_service(tmp_path / "contentops.db")
    item_id, version_id = approved_item(service, "url")

    with pytest.raises(WorkflowError, match="linkedin.com"):
        service.record_direct_publication(
            item_id, version_id, "Europe/Budapest", "direct-bad-url", post_url=post_url
        )


def test_direct_publication_cannot_be_in_the_future(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item_id, version_id = approved_item(service, "future")

    with pytest.raises(WorkflowError, match="cannot be in the future"):
        service.record_direct_publication(
            item_id,
            version_id,
            "Europe/Budapest",
            "direct-future",
            published_at=datetime.now(UTC) + timedelta(hours=1),
        )


def test_mark_published_stores_the_post_link_and_time(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item_id, version_id = approved_item(service, "marked")
    planned = service.set_publication_plan(
        item_id, version_id, datetime.now(UTC) + timedelta(days=1), "Europe/Budapest", "plan-marked-001"
    )
    assert planned.publication_plan is not None

    published = service.mark_published(item_id, planned.publication_plan.id, "mark-marked-001", post_url=POST_URL)
    assert published.publication_plan is not None
    assert published.publication_plan.post_url == POST_URL
    assert published.publication_plan.published_at is not None


def test_existing_database_gains_publication_columns(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE publication_plans (
                id TEXT PRIMARY KEY,
                content_item_id TEXT NOT NULL UNIQUE,
                version_id TEXT NOT NULL,
                planned_for TEXT NOT NULL,
                timezone TEXT NOT NULL,
                status TEXT NOT NULL,
                external_confirmation_note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
    connection.close()

    service = make_service(database)
    item_id, version_id = approved_item(service, "legacy")
    published = service.record_direct_publication(
        item_id, version_id, "Europe/Budapest", "direct-legacy", post_url=POST_URL
    )
    assert published.publication_plan is not None
    assert published.publication_plan.post_url == POST_URL

    # Initializing again must be a no-op for columns that already exist.
    SQLiteContentRepository(database)
