from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

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
from app.content.ports import ContentRepository
from app.content.repository import WorkflowError


class ContentWorkflowService:
    def __init__(self, repository: ContentRepository) -> None:
        self.repository = repository

    def get_author_memory(self) -> AuthorMemory:
        return self.repository.get_author_memory()

    def update_author_memory(self, memory: AuthorMemory, idempotency_key: str) -> AuthorMemory:
        if any(not post.title.strip() or not post.body.strip() for post in memory.past_posts):
            raise WorkflowError("Minden korábbi poszthoz cím és szöveg szükséges.")
        return self.repository.update_author_memory(memory, idempotency_key)

    def capture_idea(self, raw_idea: str, idempotency_key: str, title: str | None = None) -> ContentItemDetail:
        idea = self._required(raw_idea, "raw_idea")
        normalized_title = self._optional(title) or self._derive_title(idea)
        return self.repository.create_content_item(
            title=normalized_title,
            raw_input=idea,
            source_kind=ContentSourceKind.IDEA,
            source_urls=[],
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def capture_research(
        self,
        topic: str,
        research_notes: str,
        source_urls: list[str],
        idempotency_key: str,
    ) -> ContentItemDetail:
        normalized_urls = [self._http_url(url) for url in source_urls]
        if not normalized_urls:
            raise WorkflowError("A researched brief must include at least one source URL.")
        return self.repository.create_content_item(
            title=self._required(topic, "topic"),
            raw_input=self._required(research_notes, "research_notes"),
            source_kind=ContentSourceKind.RESEARCH,
            source_urls=normalized_urls,
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def list_content_items(self, status: ContentStatus | None, limit: int) -> ContentItemList:
        return self.repository.list_content_items(status=status, limit=limit)

    def get_content_item(self, content_item_id: str) -> ContentItemDetail:
        return self.repository.get_content_item(self._required(content_item_id, "content_item_id"))

    def save_draft_version(
        self,
        content_item_id: str,
        body: str,
        idempotency_key: str,
        change_summary: str | None = None,
        expected_current_version_id: str | None = None,
    ) -> ContentItemDetail:
        return self.repository.save_draft_version(
            content_item_id=self._required(content_item_id, "content_item_id"),
            body=self._required(body, "body"),
            change_summary=self._optional(change_summary),
            expected_current_version_id=expected_current_version_id,
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def request_changes(
        self,
        content_item_id: str,
        version_id: str,
        feedback: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        return self.repository.request_changes(
            content_item_id=self._required(content_item_id, "content_item_id"),
            version_id=self._required(version_id, "version_id"),
            message=self._required(feedback, "feedback"),
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def approve_draft(
        self,
        content_item_id: str,
        version_id: str,
        expected_content_hash: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        return self.repository.approve_draft(
            content_item_id=self._required(content_item_id, "content_item_id"),
            version_id=self._required(version_id, "version_id"),
            expected_content_hash=self._required(expected_content_hash, "expected_content_hash"),
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def revoke_approval(self, content_item_id: str, idempotency_key: str) -> ContentItemDetail:
        return self.repository.revoke_approval(
            content_item_id=self._required(content_item_id, "content_item_id"),
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def archive_content_item(self, content_item_id: str, idempotency_key: str) -> ContentItemDetail:
        return self.repository.archive_content_item(
            content_item_id=self._required(content_item_id, "content_item_id"),
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def export_workspace(self) -> WorkspaceExport:
        return self.repository.export_workspace()

    def update_writing_profile(
        self,
        style_instructions: str,
        idempotency_key: str,
        target_audience: str | None = None,
        language: str = "hu",
    ) -> WritingProfile:
        return self.repository.update_writing_profile(
            style_instructions=self._required(style_instructions, "style_instructions"),
            target_audience=self._optional(target_audience),
            language=self._required(language, "language").lower(),
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def get_writing_context(self, max_examples: int) -> WritingContext:
        return self.repository.get_writing_context(max_examples=max_examples)

    def set_publication_plan(
        self,
        content_item_id: str,
        version_id: str,
        planned_for: datetime,
        timezone: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        timezone_name = self._required(timezone, "timezone")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise WorkflowError(f"Unknown IANA timezone: {timezone_name}") from error
        if planned_for.tzinfo is None or planned_for.utcoffset() is None:
            raise WorkflowError("'planned_for' must include a UTC offset.")
        if planned_for.astimezone(UTC) <= datetime.now(UTC):
            raise WorkflowError("'planned_for' must be in the future.")
        return self.repository.set_publication_plan(
            content_item_id=self._required(content_item_id, "content_item_id"),
            version_id=self._required(version_id, "version_id"),
            planned_for=planned_for,
            timezone=timezone_name,
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def confirm_external_schedule(
        self,
        content_item_id: str,
        plan_id: str,
        confirmation_note: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        return self.repository.confirm_external_schedule(
            content_item_id=self._required(content_item_id, "content_item_id"),
            plan_id=self._required(plan_id, "plan_id"),
            confirmation_note=self._required(confirmation_note, "confirmation_note"),
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def mark_published(
        self,
        content_item_id: str,
        plan_id: str,
        idempotency_key: str,
        confirmation_note: str | None = None,
    ) -> ContentItemDetail:
        return self.repository.mark_published(
            content_item_id=self._required(content_item_id, "content_item_id"),
            plan_id=self._required(plan_id, "plan_id"),
            confirmation_note=self._optional(confirmation_note),
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    def record_performance_snapshot(
        self,
        content_item_id: str,
        idempotency_key: str,
        impressions: int | None = None,
        reactions: int | None = None,
        comments: int | None = None,
        reposts: int | None = None,
        notes: str | None = None,
    ) -> ContentItemDetail:
        normalized_notes = self._optional(notes)
        if all(metric is None for metric in (impressions, reactions, comments, reposts)) and normalized_notes is None:
            raise WorkflowError("Provide at least one metric or a note for a performance snapshot.")
        return self.repository.record_performance_snapshot(
            content_item_id=self._required(content_item_id, "content_item_id"),
            impressions=impressions,
            reactions=reactions,
            comments=comments,
            reposts=reposts,
            notes=normalized_notes,
            idempotency_key=self._required(idempotency_key, "idempotency_key"),
        )

    @staticmethod
    def _required(value: str, field_name: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise WorkflowError(f"'{field_name}' must not be empty.")
        return cleaned

    @staticmethod
    def _optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _derive_title(raw_idea: str) -> str:
        first_line = raw_idea.splitlines()[0].strip()
        return first_line[:72] + ("…" if len(first_line) > 72 else "")

    @staticmethod
    def _http_url(value: str) -> str:
        try:
            return str(TypeAdapter(AnyHttpUrl).validate_python(value.strip()))
        except ValidationError as error:
            raise WorkflowError(f"Invalid source URL: {value}") from error
