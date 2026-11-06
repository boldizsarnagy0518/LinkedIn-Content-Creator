import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from app.content.models import AuthorMemory, PastPost
from app.content.repository import ConflictError, PostgresContentRepository, SQLiteContentRepository
from app.content.service import ContentWorkflowService
from app.content.transfer import TRANSFER_TABLES, count_rows, transfer_workspace


def filled_workspace(path: Path) -> SQLiteContentRepository:
    repository = SQLiteContentRepository(path)
    service = ContentWorkflowService(repository)
    service.update_author_memory(
        AuthorMemory(background="Python developer", past_posts=[PastPost(title="Earlier", body="My own post.")]),
        "transfer-memory-001",
    )
    service.update_writing_profile("Short paragraphs.", "transfer-profile-001", "Developers", "hu")
    service.capture_idea("Only an idea", "transfer-idea-001")
    item = service.capture_research("Topic", "Notes", ["https://example.com/source"], "transfer-research-001")
    version = service.save_draft_version(item.id, "Draft one", "transfer-draft-001").versions[-1]
    service.request_changes(item.id, version.id, "Shorter", "transfer-feedback-001")
    version = service.save_draft_version(item.id, "Draft two", "transfer-draft-002").versions[-1]
    service.approve_draft(item.id, version.id, version.content_hash, "transfer-approve-001")
    service.set_publication_plan(
        item.id, version.id, datetime.now(UTC) + timedelta(days=1), "Europe/Budapest", "transfer-plan-001"
    )
    return repository


def comparable(repository: SQLiteContentRepository | PostgresContentRepository) -> dict:
    exported = repository.export_workspace().model_dump(mode="json")
    exported.pop("exported_at")
    return exported


def test_transfer_copies_the_whole_workspace_and_keeps_approvals_valid(tmp_path: Path) -> None:
    source = filled_workspace(tmp_path / "local.db")
    target = SQLiteContentRepository(tmp_path / "cloud.db")

    copied = transfer_workspace(source, target)

    assert set(copied) == set(TRANSFER_TABLES)
    assert copied == count_rows(target)
    assert comparable(target) == comparable(source)
    researched = next(item for item in target.export_workspace().content_items if item.sources)
    assert researched.active_approval is not None
    # Idempotency records travel too, so a retried write after the move is still recognized.
    service = ContentWorkflowService(target)
    assert service.capture_idea("Only an idea", "transfer-idea-001").title == "Only an idea"
    assert count_rows(target)["content_items"] == 2


def test_transfer_refuses_a_target_with_data_and_changes_nothing(tmp_path: Path) -> None:
    source = filled_workspace(tmp_path / "local.db")
    target = SQLiteContentRepository(tmp_path / "cloud.db")
    ContentWorkflowService(target).capture_idea("Already in the cloud", "cloud-idea-001")
    before = comparable(target)

    with pytest.raises(ConflictError, match="not empty"):
        transfer_workspace(source, target)

    assert comparable(target) == before


def test_transfer_into_real_postgres() -> None:
    database_url = os.environ.get("CONTENTOPS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CONTENTOPS_TEST_DATABASE_URL to run the isolated Postgres transfer test")
    schema = f"contentops_transfer_{uuid4().hex}"
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    separator = "&" if "?" in database_url else "?"
    scoped_url = f"{database_url}{separator}options={quote(f'-c search_path={schema}')}"
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            source = filled_workspace(Path(directory) / "local.db")
            target = PostgresContentRepository(scoped_url)
            transfer_workspace(source, target)
            assert comparable(target) == comparable(source)
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
