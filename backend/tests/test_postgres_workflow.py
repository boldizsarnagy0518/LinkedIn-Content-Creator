import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from app.content.models import AuthorMemory, PastPost
from app.content.repository import ConflictError, PostgresContentRepository
from app.content.service import ContentWorkflowService


@pytest.fixture
def postgres_service():
    database_url = os.environ.get("CONTENTOPS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set CONTENTOPS_TEST_DATABASE_URL to run the isolated Postgres integration test")
    schema = f"contentops_test_{uuid4().hex}"
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    separator = "&" if "?" in database_url else "?"
    scoped_url = f"{database_url}{separator}options={quote(f'-c search_path={schema}')}"
    try:
        yield ContentWorkflowService(PostgresContentRepository(scoped_url))
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_real_postgres_capture_review_publication_and_parallel_retries(postgres_service):
    service = postgres_service
    memory = service.update_author_memory(AuthorMemory(
        background="Portfolio developer", past_posts=[PastPost(title="Earlier post", body="My own writing.")],
    ), "pg-author-memory-001")
    assert service.get_writing_context(5).author_memory == memory
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.capture_idea("Walking note", "pg-idea-retry-001"), range(2)))
    assert results[0].id == results[1].id
    researched = service.capture_research("A topic", "Evidence", ["https://example.com/source"], "pg-research-001")
    assert len(researched.sources) == 1
    drafted = service.save_draft_version(
        researched.id, "Reviewed copy", "pg-draft-001", expected_current_version_id="source"
    )
    version = drafted.versions[-1]
    with pytest.raises(ConflictError):
        service.save_draft_version(researched.id, "Stale copy", "pg-stale-001", expected_current_version_id="source")
    approved = service.approve_draft(researched.id, version.id, version.content_hash, "pg-approve-001")
    assert approved.active_approval is not None
    planned = service.set_publication_plan(
        researched.id, version.id, datetime.now(UTC) + timedelta(days=1), "Europe/Budapest", "pg-plan-001"
    )
    assert planned.publication_plan is not None
    service.mark_published(researched.id, planned.publication_plan.id, "pg-published-001")
    measured = service.record_performance_snapshot(researched.id, "pg-metrics-001", impressions=100)
    assert measured.performance_snapshots[0].impressions == 100
    assert len(service.export_workspace().content_items) == 2
    assert service.export_workspace().author_memory == memory
