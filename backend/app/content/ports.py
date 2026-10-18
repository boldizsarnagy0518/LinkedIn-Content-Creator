from datetime import datetime
from typing import Protocol

from app.content.models import (
    AuthorMemory,
    ContentItemDetail,
    ContentItemList,
    ContentSourceKind,
    ContentStatus,
    WorkspaceExport,
    WritingContext,
    WritingProfile,
)


class ContentRepository(Protocol):
    """Persistence boundary used by the HTTP and MCP application services."""

    def get_author_memory(self) -> AuthorMemory: ...

    def update_author_memory(self, memory: AuthorMemory, idempotency_key: str) -> AuthorMemory: ...

    def create_content_item(
        self,
        *,
        title: str,
        raw_input: str,
        source_kind: ContentSourceKind,
        source_urls: list[str],
        idempotency_key: str,
    ) -> ContentItemDetail: ...

    def list_content_items(self, status: ContentStatus | None, limit: int) -> ContentItemList: ...

    def get_content_item(self, content_item_id: str) -> ContentItemDetail: ...

    def save_draft_version(
        self,
        *,
        content_item_id: str,
        body: str,
        change_summary: str | None,
        idempotency_key: str,
        expected_current_version_id: str | None = None,
    ) -> ContentItemDetail: ...

    def request_changes(
        self,
        *,
        content_item_id: str,
        version_id: str,
        message: str,
        idempotency_key: str,
    ) -> ContentItemDetail: ...

    def approve_draft(
        self,
        *,
        content_item_id: str,
        version_id: str,
        expected_content_hash: str,
        idempotency_key: str,
    ) -> ContentItemDetail: ...

    def revoke_approval(self, *, content_item_id: str, idempotency_key: str) -> ContentItemDetail: ...

    def archive_content_item(self, *, content_item_id: str, idempotency_key: str) -> ContentItemDetail: ...

    def update_writing_profile(
        self,
        *,
        style_instructions: str,
        target_audience: str | None,
        language: str,
        idempotency_key: str,
    ) -> WritingProfile: ...

    def get_writing_context(self, max_examples: int) -> WritingContext: ...

    def set_publication_plan(
        self,
        *,
        content_item_id: str,
        version_id: str,
        planned_for: datetime,
        timezone: str,
        idempotency_key: str,
    ) -> ContentItemDetail: ...

    def confirm_external_schedule(
        self,
        *,
        content_item_id: str,
        plan_id: str,
        confirmation_note: str,
        idempotency_key: str,
    ) -> ContentItemDetail: ...

    def mark_published(
        self,
        *,
        content_item_id: str,
        plan_id: str,
        confirmation_note: str | None,
        idempotency_key: str,
    ) -> ContentItemDetail: ...

    def record_performance_snapshot(
        self,
        *,
        content_item_id: str,
        impressions: int | None,
        reactions: int | None,
        comments: int | None,
        reposts: int | None,
        notes: str | None,
        idempotency_key: str,
    ) -> ContentItemDetail: ...

    def export_workspace(self) -> WorkspaceExport: ...
