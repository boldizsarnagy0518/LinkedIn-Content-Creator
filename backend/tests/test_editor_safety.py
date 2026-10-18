from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import pytest

from app.content.models import ContentStatus
from app.content.repository import ConflictError, SQLiteContentRepository
from app.content.service import ContentWorkflowService


def test_stale_editor_cannot_save_over_newer_work(tmp_path: Path) -> None:
    service = ContentWorkflowService(SQLiteContentRepository(tmp_path / "editor.db"))
    item = service.capture_idea("A walking idea", "capture-editor-001")
    first = service.save_draft_version(
        item.id, "First draft", "draft-editor-001", expected_current_version_id="source"
    )
    with pytest.raises(ConflictError, match="newer draft"):
        service.save_draft_version(item.id, "Stale draft", "draft-editor-002", expected_current_version_id="source")
    second = service.save_draft_version(
        item.id, "Reviewed edit", "draft-editor-003", expected_current_version_id=first.current_version_id
    )
    # A retry replays before checking the now-outdated base version.
    replay = service.save_draft_version(
        item.id, "Reviewed edit", "draft-editor-003", expected_current_version_id=first.current_version_id
    )
    assert replay == second
    assert [v.body for v in service.get_content_item(item.id).versions] == ["First draft", "Reviewed edit"]


def test_parallel_approval_and_save_cannot_leave_an_approved_unreviewed_version(tmp_path: Path) -> None:
    path = tmp_path / "race.db"
    approving_repo = SQLiteContentRepository(path)
    approving = ContentWorkflowService(approving_repo)
    writing = ContentWorkflowService(SQLiteContentRepository(path))
    item = writing.capture_idea("A concurrent idea", "capture-race-001")
    version = writing.save_draft_version(item.id, "First draft", "draft-race-001").versions[-1]
    read_done, release_read, write_started, write_finished = Event(), Event(), Event(), Event()
    original = approving_repo._get_content_item
    paused = False

    def pause_once(connection, content_item_id):
        nonlocal paused
        result = original(connection, content_item_id)
        if not paused:
            paused = True
            read_done.set()
            assert release_read.wait(5)
        return result

    approving_repo._get_content_item = pause_once

    def save():
        write_started.set()
        try:
            return writing.save_draft_version(item.id, "Second draft", "draft-race-002")
        finally:
            write_finished.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        approval = pool.submit(approving.approve_draft, item.id, version.id, version.content_hash, "approval-race-001")
        try:
            assert read_done.wait(5)
            writer = pool.submit(save)
            assert write_started.wait(5)
            assert not write_finished.wait(0.2), "Writer must wait for the approval transaction"
        finally:
            release_read.set()
        assert approval.result(timeout=5).active_approval is not None
        assert writer.result(timeout=5).status == ContentStatus.DRAFT
    latest = writing.get_content_item(item.id)
    assert latest.current_version_id != version.id
    assert latest.status == ContentStatus.DRAFT
    assert latest.active_approval is None


def test_parallel_retries_create_one_idea(tmp_path: Path) -> None:
    path = tmp_path / "retries.db"
    services = [ContentWorkflowService(SQLiteContentRepository(path)) for _ in range(2)]
    barrier = Barrier(2)

    def capture(service):
        barrier.wait(timeout=5)
        return service.capture_idea("Save for later only", "same-capture-key")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(capture, services))
    assert results[0].id == results[1].id
    assert results[0].versions == []
    assert services[0].list_content_items(None, 100).count == 1


def test_connections_are_closed_after_repository_calls(tmp_path: Path) -> None:
    path = tmp_path / "closed.db"
    service = ContentWorkflowService(SQLiteContentRepository(path))
    service.capture_idea("Close the SQLite connection", "capture-close-001")
    service.list_content_items(None, 100)
    path.unlink()  # On Windows this fails if a connection still holds the database open.
    assert not path.exists()
