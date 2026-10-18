from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.content.models import ContentStatus, PublicationPlanStatus
from app.content.repository import ConflictError, SQLiteContentRepository
from app.content.service import ContentWorkflowService


def make_service(database_path: Path) -> ContentWorkflowService:
    return ContentWorkflowService(SQLiteContentRepository(database_path))


def test_full_review_flow_keeps_versions_and_invalidates_stale_approval(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")

    item = service.capture_idea(
        raw_idea="Az AI nem stratégia, ha nincs mögötte ismételhető workflow.",
        title="AI workflow",
        idempotency_key="idea-request-001",
    )
    assert item.status is ContentStatus.CAPTURED

    version_one = service.save_draft_version(
        content_item_id=item.id,
        body="Az AI önmagában nem stratégia. Az ismételhető workflow az.",
        idempotency_key="draft-request-001",
    )
    first = version_one.versions[-1]
    approved = service.approve_draft(
        content_item_id=item.id,
        version_id=first.id,
        expected_content_hash=first.content_hash,
        idempotency_key="approve-request-001",
    )
    assert approved.status is ContentStatus.APPROVED
    assert approved.active_approval is not None

    writing_context = service.get_writing_context(max_examples=5)
    assert [example.body for example in writing_context.approved_examples] == [first.body]

    version_two = service.save_draft_version(
        content_item_id=item.id,
        body="Az AI nem stratégia. Az ismételhető, mérhető workflow viszont az.",
        change_summary="Pontosabb állítás",
        idempotency_key="draft-request-002",
    )
    second = version_two.versions[-1]
    assert second.id != first.id
    assert version_two.status is ContentStatus.DRAFT
    assert version_two.active_approval is None
    assert len(version_two.versions) == 2
    assert service.get_writing_context(max_examples=5).approved_examples == []

    with pytest.raises(ConflictError, match="current draft version"):
        service.approve_draft(
            content_item_id=item.id,
            version_id=first.id,
            expected_content_hash=first.content_hash,
            idempotency_key="approve-request-stale",
        )


def test_mutating_calls_are_retry_safe_with_idempotency_keys(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")

    first = service.capture_idea("Egy nyers ötlet", "idea-repeat-001")
    replay = service.capture_idea("Egy nyers ötlet", "idea-repeat-001")
    assert replay.id == first.id

    with pytest.raises(ConflictError, match="different create_content_item request"):
        service.capture_idea("Másik ötlet", "idea-repeat-001")

    drafted = service.save_draft_version(first.id, "Első draft", "draft-repeat-001")
    draft_replay = service.save_draft_version(first.id, "Első draft", "draft-repeat-001")
    assert len(draft_replay.versions) == 1
    assert draft_replay.current_version_id == drafted.current_version_id


def test_feedback_must_target_current_version(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item = service.capture_idea("Ötlet", "idea-feedback-001")
    first = service.save_draft_version(item.id, "V1", "draft-feedback-001").versions[-1]
    second = service.save_draft_version(item.id, "V2", "draft-feedback-002").versions[-1]

    with pytest.raises(ConflictError, match="current draft version"):
        service.request_changes(item.id, first.id, "Legyen konkrétabb.", "feedback-stale-001")

    changed = service.request_changes(item.id, second.id, "Legyen konkrétabb.", "feedback-current-001")
    assert changed.status is ContentStatus.CHANGES_REQUESTED
    assert changed.feedback[-1].version_id == second.id

    with pytest.raises(ConflictError, match="new draft version"):
        service.approve_draft(
            item.id,
            second.id,
            second.content_hash,
            "approve-without-revision",
        )


def test_approval_can_be_revoked_and_items_can_be_archived(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item = service.capture_idea("Approval remains a deliberate action.", "idea-lifecycle-001")
    version = service.save_draft_version(item.id, "A reviewed draft.", "draft-lifecycle-001").versions[-1]
    service.approve_draft(item.id, version.id, version.content_hash, "approve-lifecycle-001")

    revoked = service.revoke_approval(item.id, "revoke-lifecycle-001")
    assert revoked.status is ContentStatus.DRAFT
    assert revoked.active_approval is None

    archived = service.archive_content_item(item.id, "archive-lifecycle-001")
    assert archived.status is ContentStatus.ARCHIVED
    assert service.list_content_items(status=None, limit=20).items == []
    assert service.list_content_items(status=ContentStatus.ARCHIVED, limit=20).items[0].id == item.id
    assert service.export_workspace().content_items[0].id == item.id


def test_writing_profile_and_research_sources_are_durable(tmp_path: Path) -> None:
    database_path = tmp_path / "contentops.db"
    service = make_service(database_path)
    profile = service.update_writing_profile(
        style_instructions="Rövid mondatok. Konkrét példák. Kerüld a hype-ot.",
        target_audience="Magyar szoftverfejlesztők",
        language="HU",
        idempotency_key="profile-request-001",
    )
    service.capture_research(
        topic="AI workflow-k",
        research_notes="Ellenőrzött összefoglaló.",
        source_urls=["https://example.com/report", "https://example.com/report"],
        idempotency_key="research-request-001",
    )

    reopened = make_service(database_path)
    context = reopened.get_writing_context(max_examples=5)
    research_items = reopened.list_content_items(status=None, limit=20)

    assert context.profile == profile
    assert context.profile.language == "hu"
    assert research_items.count == 1
    detail = reopened.get_content_item(research_items.items[0].id)
    assert [source.url for source in detail.sources] == ["https://example.com/report"]


def test_publication_state_requires_approval_and_never_implies_external_action(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item = service.capture_idea("A durable workflow needs explicit state.", "idea-plan-001")
    drafted = service.save_draft_version(item.id, "Reviewed draft", "draft-plan-001")
    version = drafted.versions[-1]
    planned_for = datetime.now(UTC) + timedelta(days=2)

    with pytest.raises(ConflictError, match="currently approved"):
        service.set_publication_plan(
            item.id,
            version.id,
            planned_for,
            "Europe/Budapest",
            "plan-before-approval",
        )

    service.approve_draft(item.id, version.id, version.content_hash, "approve-plan-001")
    planned = service.set_publication_plan(
        item.id,
        version.id,
        planned_for,
        "Europe/Budapest",
        "plan-approved-001",
    )
    assert planned.publication_plan is not None
    assert planned.publication_plan.status is PublicationPlanStatus.PLANNED

    confirmed = service.confirm_external_schedule(
        item.id,
        planned.publication_plan.id,
        "Confirmed manually in LinkedIn.",
        "confirm-schedule-001",
    )
    assert confirmed.publication_plan is not None
    assert confirmed.publication_plan.status is PublicationPlanStatus.SCHEDULED_EXTERNALLY

    published = service.mark_published(
        item.id,
        confirmed.publication_plan.id,
        "mark-published-001",
        "Live URL checked manually.",
    )
    assert published.publication_plan is not None
    assert published.publication_plan.status is PublicationPlanStatus.PUBLISHED
    measured = service.record_performance_snapshot(
        item.id,
        "performance-snapshot-001",
        impressions=1200,
        reactions=42,
        comments=7,
        reposts=3,
        notes="Manual 24-hour snapshot.",
    )
    assert measured.performance_snapshots[0].impressions == 1200
    assert measured.performance_snapshots[0].publication_plan_id == published.publication_plan.id
    assert [event.event_type for event in measured.events[:4]] == [
        "performance_snapshot_recorded",
        "publication_confirmed",
        "external_schedule_confirmed",
        "publication_planned",
    ]


def test_new_version_cancels_a_stale_publication_plan(tmp_path: Path) -> None:
    service = make_service(tmp_path / "contentops.db")
    item = service.capture_idea("Version safety", "idea-cancel-plan")
    first = service.save_draft_version(item.id, "Version one", "draft-cancel-001").versions[-1]
    service.approve_draft(item.id, first.id, first.content_hash, "approve-cancel-001")
    planned = service.set_publication_plan(
        item.id,
        first.id,
        datetime.now(UTC) + timedelta(days=1),
        "Europe/Budapest",
        "plan-cancel-001",
    )
    assert planned.publication_plan is not None

    changed = service.save_draft_version(item.id, "Version two", "draft-cancel-002")
    assert changed.publication_plan is not None
    assert changed.publication_plan.status is PublicationPlanStatus.CANCELLED
    assert changed.active_approval is None
