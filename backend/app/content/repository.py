from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel

from app.content.models import (
    Approval,
    AuthorMemory,
    ContentItemDetail,
    ContentItemList,
    ContentItemSummary,
    ContentSourceKind,
    ContentStatus,
    DraftVersion,
    PerformanceSnapshot,
    PublicationPlan,
    PublicationPlanStatus,
    ReviewFeedback,
    SourceReference,
    WorkflowEvent,
    WorkspaceExport,
    WritingContext,
    WritingExample,
    WritingProfile,
)


class WorkflowError(RuntimeError):
    """A model-readable workflow error."""


class NotFoundError(WorkflowError):
    pass


class ConflictError(WorkflowError):
    pass


ModelT = TypeVar("ModelT", bound=BaseModel)


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_text(normalized)


class _PostgresConnection:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def __enter__(self) -> _PostgresConnection:
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.connection.__exit__(exc_type, exc_value, traceback)

    def execute(self, query: str, parameters: Iterable[Any] = ()) -> Any:
        return self.connection.execute(query.replace("?", "%s"), tuple(parameters))

    def executemany(self, query: str, parameters: Iterable[Iterable[Any]]) -> None:
        with self.connection.cursor() as cursor:
            cursor.executemany(query.replace("?", "%s"), [tuple(values) for values in parameters])

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            if statement.strip():
                self.connection.execute(statement)


class SqlContentRepository:
    def __init__(self, database: Path | str) -> None:
        value = str(database)
        self.database_url = value if value.startswith(("postgresql://", "postgres://")) else None
        self.database_path = None if self.database_url else Path(database)
        if self.database_path is not None:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connect(self, *, write: bool = False) -> Iterator[Any]:
        if self.database_url is not None:
            from psycopg import connect
            from psycopg.rows import dict_row

            with _PostgresConnection(connect(self.database_url, row_factory=dict_row)) as connection:
                if write:
                    # One owner, one workspace: serialize short mutations across API/MCP processes,
                    # including idempotency checks. No network/model work runs inside this lock.
                    connection.execute("SELECT pg_advisory_xact_lock(734019265)")
                else:
                    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                yield connection
            return
        with closing(sqlite3.connect(self.database_path, timeout=10)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            with connection:
                connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield connection

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS content_items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            raw_input TEXT NOT NULL,
            status TEXT NOT NULL,
            current_version_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS source_references (
            id TEXT PRIMARY KEY,
            content_item_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            title TEXT,
            note TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS draft_versions (
            id TEXT PRIMARY KEY,
            content_item_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            body TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            change_summary TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(content_item_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS review_feedback (
            id TEXT PRIMARY KEY,
            content_item_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            version_id TEXT NOT NULL REFERENCES draft_versions(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            content_item_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            version_id TEXT NOT NULL REFERENCES draft_versions(id) ON DELETE CASCADE,
            content_hash TEXT NOT NULL,
            approved_at TEXT NOT NULL,
            UNIQUE(content_item_id, version_id, content_hash)
        );

        CREATE TABLE IF NOT EXISTS writing_profiles (
            id TEXT PRIMARY KEY CHECK (id = 'default'),
            style_instructions TEXT NOT NULL,
            target_audience TEXT,
            language TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS author_memory (
            id TEXT PRIMARY KEY CHECK (id = 'default'),
            payload TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS publication_plans (
            id TEXT PRIMARY KEY,
            content_item_id TEXT NOT NULL UNIQUE REFERENCES content_items(id) ON DELETE CASCADE,
            version_id TEXT NOT NULL REFERENCES draft_versions(id) ON DELETE CASCADE,
            planned_for TEXT NOT NULL,
            timezone TEXT NOT NULL,
            status TEXT NOT NULL,
            external_confirmation_note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workflow_events (
            id TEXT PRIMARY KEY,
            content_item_id TEXT REFERENCES content_items(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS performance_snapshots (
            id TEXT PRIMARY KEY,
            content_item_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            publication_plan_id TEXT NOT NULL REFERENCES publication_plans(id) ON DELETE CASCADE,
            impressions INTEGER,
            reactions INTEGER,
            comments INTEGER,
            reposts INTEGER,
            notes TEXT,
            recorded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS idempotency_records (
            operation TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(operation, idempotency_key)
        );

        CREATE INDEX IF NOT EXISTS idx_content_items_updated_at ON content_items(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_draft_versions_item ON draft_versions(content_item_id, version_number);
        CREATE INDEX IF NOT EXISTS idx_feedback_item ON review_feedback(content_item_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_workflow_events_item ON workflow_events(content_item_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_performance_snapshots_item
            ON performance_snapshots(content_item_id, recorded_at DESC);
        """
        with self._connect(write=True) as connection:
            connection.executescript(schema)
            connection.execute(
                """
                INSERT INTO writing_profiles
                    (id, style_instructions, target_audience, language, updated_at)
                VALUES ('default', ?, NULL, 'hu', ?)
                ON CONFLICT DO NOTHING
                """,
                (
                    "Write clearly and specifically. Preserve the author's point of view; "
                    "do not invent experience or facts.",
                    _now().isoformat(),
                ),
            )

    def _replay(
        self,
        connection: Any,
        operation: str,
        idempotency_key: str,
        payload: dict[str, Any],
        model_type: type[ModelT],
    ) -> ModelT | None:
        row = connection.execute(
            "SELECT request_hash, response_json FROM idempotency_records WHERE operation = ? AND idempotency_key = ?",
            (operation, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != _request_hash(payload):
            raise ConflictError(
                f"Idempotency key '{idempotency_key}' was already used for a different {operation} request."
            )
        return model_type.model_validate_json(row["response_json"])

    def _remember(
        self,
        connection: Any,
        operation: str,
        idempotency_key: str,
        payload: dict[str, Any],
        response: BaseModel,
    ) -> None:
        connection.execute(
            """
            INSERT INTO idempotency_records
                (operation, idempotency_key, request_hash, response_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                operation,
                idempotency_key,
                _request_hash(payload),
                response.model_dump_json(),
                _now().isoformat(),
            ),
        )

    def create_content_item(
        self,
        *,
        title: str,
        raw_input: str,
        source_kind: ContentSourceKind,
        source_urls: Iterable[str],
        idempotency_key: str,
    ) -> ContentItemDetail:
        urls = list(dict.fromkeys(source_urls))
        payload = {
            "title": title,
            "raw_input": raw_input,
            "source_kind": source_kind.value,
            "source_urls": urls,
        }
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "create_content_item", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay

            item_id = uuid4().hex
            timestamp = _now().isoformat()
            connection.execute(
                """
                INSERT INTO content_items
                    (id, title, source_kind, raw_input, status, current_version_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (item_id, title, source_kind.value, raw_input, ContentStatus.CAPTURED.value, timestamp, timestamp),
            )
            connection.executemany(
                """
                INSERT INTO source_references (id, content_item_id, url, title, note, created_at)
                VALUES (?, ?, ?, NULL, NULL, ?)
                """,
                [(uuid4().hex, item_id, url, timestamp) for url in urls],
            )
            self._record_event(
                connection,
                content_item_id=item_id,
                event_type="content_captured",
                details={"source_kind": source_kind.value},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, item_id)
            self._remember(connection, "create_content_item", idempotency_key, payload, result)
            return result

    def list_content_items(self, status: ContentStatus | None, limit: int) -> ContentItemList:
        query = "SELECT * FROM content_items"
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status.value)
        else:
            query += " WHERE status != ?"
            params.append(ContentStatus.ARCHIVED.value)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        items = [self._summary_from_row(row) for row in rows]
        return ContentItemList(items=items, count=len(items))

    def get_content_item(self, content_item_id: str) -> ContentItemDetail:
        with self._connect() as connection:
            return self._get_content_item(connection, content_item_id)

    def save_draft_version(
        self,
        *,
        content_item_id: str,
        body: str,
        change_summary: str | None,
        idempotency_key: str,
        expected_current_version_id: str | None = None,
    ) -> ContentItemDetail:
        payload = {
            "content_item_id": content_item_id,
            "body": body,
            "change_summary": change_summary,
        }
        if expected_current_version_id is not None:
            payload["expected_current_version_id"] = expected_current_version_id
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "save_draft_version", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            current = self._get_content_item(connection, content_item_id)
            if current.status is ContentStatus.ARCHIVED:
                raise ConflictError("Archived content cannot receive a new draft version.")
            if (
                expected_current_version_id is not None
                and expected_current_version_id != (current.current_version_id or "source")
            ):
                raise ConflictError("A newer draft is available. Review it before saving your changes.")
            content_hash = _hash_text(body)
            if current.versions and current.versions[-1].content_hash == content_hash:
                result = current
            else:
                version_id = uuid4().hex
                version_number = len(current.versions) + 1
                timestamp = _now().isoformat()
                connection.execute(
                    """
                    INSERT INTO draft_versions
                        (id, content_item_id, version_number, body, content_hash, change_summary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (version_id, content_item_id, version_number, body, content_hash, change_summary, timestamp),
                )
                connection.execute(
                    """
                    UPDATE content_items
                    SET current_version_id = ?, status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (version_id, ContentStatus.DRAFT.value, timestamp, content_item_id),
                )
                self._cancel_active_plan(connection, content_item_id, timestamp)
                self._record_event(
                    connection,
                    content_item_id=content_item_id,
                    event_type="draft_version_saved",
                    details={"version_id": version_id, "version_number": version_number},
                    timestamp=timestamp,
                )
                result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "save_draft_version", idempotency_key, payload, result)
            return result

    def request_changes(
        self,
        *,
        content_item_id: str,
        version_id: str,
        message: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        payload = {"content_item_id": content_item_id, "version_id": version_id, "message": message}
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "request_changes", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            current = self._get_content_item(connection, content_item_id)
            if current.status is ContentStatus.ARCHIVED:
                raise ConflictError("Archived content cannot receive feedback.")
            if current.current_version_id != version_id:
                raise ConflictError("Feedback must target the current draft version.")
            timestamp = _now().isoformat()
            connection.execute(
                """
                INSERT INTO review_feedback (id, content_item_id, version_id, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (uuid4().hex, content_item_id, version_id, message, timestamp),
            )
            connection.execute(
                "UPDATE content_items SET status = ?, updated_at = ? WHERE id = ?",
                (ContentStatus.CHANGES_REQUESTED.value, timestamp, content_item_id),
            )
            self._cancel_active_plan(connection, content_item_id, timestamp)
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="changes_requested",
                details={"version_id": version_id},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "request_changes", idempotency_key, payload, result)
            return result

    def approve_draft(
        self,
        *,
        content_item_id: str,
        version_id: str,
        expected_content_hash: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        payload = {
            "content_item_id": content_item_id,
            "version_id": version_id,
            "expected_content_hash": expected_content_hash,
        }
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "approve_draft", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            current = self._get_content_item(connection, content_item_id)
            if current.status is ContentStatus.CHANGES_REQUESTED:
                raise ConflictError("Save a new draft version before approving requested changes.")
            if current.status is ContentStatus.ARCHIVED:
                raise ConflictError("Archived content cannot be approved.")
            if current.current_version_id != version_id:
                raise ConflictError("Only the current draft version can be approved.")
            version = next((candidate for candidate in current.versions if candidate.id == version_id), None)
            if version is None:
                raise NotFoundError(f"Draft version '{version_id}' was not found.")
            if version.content_hash != expected_content_hash:
                raise ConflictError("The draft content changed. Review the current content hash before approving it.")
            timestamp = _now().isoformat()
            connection.execute(
                """
                INSERT INTO approvals
                    (id, content_item_id, version_id, content_hash, approved_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (uuid4().hex, content_item_id, version_id, expected_content_hash, timestamp),
            )
            connection.execute(
                "UPDATE content_items SET status = ?, updated_at = ? WHERE id = ?",
                (ContentStatus.APPROVED.value, timestamp, content_item_id),
            )
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="draft_approved",
                details={"version_id": version_id, "content_hash": expected_content_hash},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "approve_draft", idempotency_key, payload, result)
            return result

    def revoke_approval(self, *, content_item_id: str, idempotency_key: str) -> ContentItemDetail:
        payload = {"content_item_id": content_item_id}
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "revoke_approval", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            current = self._get_content_item(connection, content_item_id)
            if current.status is not ContentStatus.APPROVED or current.active_approval is None:
                raise ConflictError("Only an actively approved draft can have its approval revoked.")
            timestamp = _now().isoformat()
            connection.execute(
                "UPDATE content_items SET status = ?, updated_at = ? WHERE id = ?",
                (ContentStatus.DRAFT.value, timestamp, content_item_id),
            )
            self._cancel_active_plan(connection, content_item_id, timestamp)
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="approval_revoked",
                details={"version_id": current.active_approval.version_id},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "revoke_approval", idempotency_key, payload, result)
            return result

    def archive_content_item(self, *, content_item_id: str, idempotency_key: str) -> ContentItemDetail:
        payload = {"content_item_id": content_item_id}
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "archive_content_item", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            current = self._get_content_item(connection, content_item_id)
            if current.status is ContentStatus.ARCHIVED:
                raise ConflictError("Content item is already archived.")
            timestamp = _now().isoformat()
            self._cancel_active_plan(connection, content_item_id, timestamp)
            connection.execute(
                "UPDATE content_items SET status = ?, updated_at = ? WHERE id = ?",
                (ContentStatus.ARCHIVED.value, timestamp, content_item_id),
            )
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="content_archived",
                details={"previous_status": current.status.value},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "archive_content_item", idempotency_key, payload, result)
            return result

    def update_writing_profile(
        self,
        *,
        style_instructions: str,
        target_audience: str | None,
        language: str,
        idempotency_key: str,
    ) -> WritingProfile:
        payload = {
            "style_instructions": style_instructions,
            "target_audience": target_audience,
            "language": language,
        }
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "update_writing_profile", idempotency_key, payload, WritingProfile)
            if replay is not None:
                return replay
            timestamp = _now().isoformat()
            connection.execute(
                """
                UPDATE writing_profiles
                SET style_instructions = ?, target_audience = ?, language = ?, updated_at = ?
                WHERE id = 'default'
                """,
                (style_instructions, target_audience, language, timestamp),
            )
            result = WritingProfile(
                style_instructions=style_instructions,
                target_audience=target_audience,
                language=language,
                updated_at=datetime.fromisoformat(timestamp),
            )
            self._record_event(
                connection,
                content_item_id=None,
                event_type="writing_profile_updated",
                details={"language": language},
                timestamp=timestamp,
            )
            self._remember(connection, "update_writing_profile", idempotency_key, payload, result)
            return result

    def set_publication_plan(
        self,
        *,
        content_item_id: str,
        version_id: str,
        planned_for: datetime,
        timezone: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        planned_for_iso = planned_for.isoformat()
        payload = {
            "content_item_id": content_item_id,
            "version_id": version_id,
            "planned_for": planned_for_iso,
            "timezone": timezone,
        }
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "set_publication_plan", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            current = self._get_content_item(connection, content_item_id)
            if current.current_version_id != version_id or current.active_approval is None:
                raise ConflictError("Only the currently approved exact draft version can be planned.")

            existing = connection.execute(
                "SELECT id, status FROM publication_plans WHERE content_item_id = ?",
                (content_item_id,),
            ).fetchone()
            if existing is not None and existing["status"] == PublicationPlanStatus.PUBLISHED.value:
                raise ConflictError("A published plan cannot be replaced.")

            timestamp = _now().isoformat()
            plan_id = existing["id"] if existing is not None else uuid4().hex
            connection.execute(
                """
                INSERT INTO publication_plans
                    (id, content_item_id, version_id, planned_for, timezone, status,
                     external_confirmation_note, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                ON CONFLICT(content_item_id) DO UPDATE SET
                    version_id = excluded.version_id,
                    planned_for = excluded.planned_for,
                    timezone = excluded.timezone,
                    status = excluded.status,
                    external_confirmation_note = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    plan_id,
                    content_item_id,
                    version_id,
                    planned_for_iso,
                    timezone,
                    PublicationPlanStatus.PLANNED.value,
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute("UPDATE content_items SET updated_at = ? WHERE id = ?", (timestamp, content_item_id))
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="publication_planned",
                details={"plan_id": plan_id, "version_id": version_id, "planned_for": planned_for_iso},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "set_publication_plan", idempotency_key, payload, result)
            return result

    def confirm_external_schedule(
        self,
        *,
        content_item_id: str,
        plan_id: str,
        confirmation_note: str,
        idempotency_key: str,
    ) -> ContentItemDetail:
        payload = {
            "content_item_id": content_item_id,
            "plan_id": plan_id,
            "confirmation_note": confirmation_note,
        }
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "confirm_external_schedule", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            plan = self._require_plan(connection, content_item_id, plan_id)
            if plan["status"] != PublicationPlanStatus.PLANNED.value:
                raise ConflictError("Only an internally planned post can be confirmed as externally scheduled.")
            timestamp = _now().isoformat()
            connection.execute(
                """
                UPDATE publication_plans
                SET status = ?, external_confirmation_note = ?, updated_at = ?
                WHERE id = ?
                """,
                (PublicationPlanStatus.SCHEDULED_EXTERNALLY.value, confirmation_note, timestamp, plan_id),
            )
            connection.execute("UPDATE content_items SET updated_at = ? WHERE id = ?", (timestamp, content_item_id))
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="external_schedule_confirmed",
                details={"plan_id": plan_id},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "confirm_external_schedule", idempotency_key, payload, result)
            return result

    def mark_published(
        self,
        *,
        content_item_id: str,
        plan_id: str,
        confirmation_note: str | None,
        idempotency_key: str,
    ) -> ContentItemDetail:
        payload = {
            "content_item_id": content_item_id,
            "plan_id": plan_id,
            "confirmation_note": confirmation_note,
        }
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "mark_published", idempotency_key, payload, ContentItemDetail)
            if replay is not None:
                return replay
            plan = self._require_plan(connection, content_item_id, plan_id)
            if plan["status"] not in {
                PublicationPlanStatus.PLANNED.value,
                PublicationPlanStatus.SCHEDULED_EXTERNALLY.value,
            }:
                raise ConflictError("Only a planned or externally scheduled post can be marked as published.")
            timestamp = _now().isoformat()
            note = confirmation_note or plan["external_confirmation_note"]
            connection.execute(
                """
                UPDATE publication_plans
                SET status = ?, external_confirmation_note = ?, updated_at = ?
                WHERE id = ?
                """,
                (PublicationPlanStatus.PUBLISHED.value, note, timestamp, plan_id),
            )
            connection.execute("UPDATE content_items SET updated_at = ? WHERE id = ?", (timestamp, content_item_id))
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="publication_confirmed",
                details={"plan_id": plan_id},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "mark_published", idempotency_key, payload, result)
            return result

    def get_author_memory(self) -> AuthorMemory:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM author_memory WHERE id = 'default'").fetchone()
            return AuthorMemory.model_validate_json(row["payload"]) if row else AuthorMemory()

    def update_author_memory(self, memory: AuthorMemory, idempotency_key: str) -> AuthorMemory:
        payload = memory.model_dump(mode="json")
        with self._connect(write=True) as connection:
            replay = self._replay(connection, "update_author_memory", idempotency_key, payload, AuthorMemory)
            if replay is not None:
                return replay
            row = connection.execute("SELECT payload FROM author_memory WHERE id = 'default'").fetchone()
            current = AuthorMemory.model_validate_json(row["payload"]) if row else AuthorMemory()
            if current.revision != memory.revision:
                raise ConflictError("A profil vagy a posztgyűjtemény közben megváltozott. Töltsd újra mentés előtt.")
            result = memory.model_copy(update={"revision": uuid4().hex})
            connection.execute(
                "INSERT INTO author_memory (id, payload) VALUES ('default', ?) "
                "ON CONFLICT (id) DO UPDATE SET payload = excluded.payload",
                (result.model_dump_json(),),
            )
            self._record_event(connection, content_item_id=None, event_type="author_memory_updated",
                               details={"post_count": len(result.past_posts)}, timestamp=_now().isoformat())
            self._remember(connection, "update_author_memory", idempotency_key, payload, result)
            return result

    def get_writing_context(self, max_examples: int) -> WritingContext:
        with self._connect() as connection:
            profile_row = connection.execute("SELECT * FROM writing_profiles WHERE id = 'default'").fetchone()
            memory_row = connection.execute("SELECT payload FROM author_memory WHERE id = 'default'").fetchone()
            example_rows = connection.execute(
                """
                WITH candidates AS (
                    SELECT
                        ci.id AS content_item_id,
                        ci.title,
                        dv.body,
                        a.approved_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY ci.id
                            ORDER BY a.approved_at DESC
                        ) AS item_rank
                    FROM approvals a
                    JOIN content_items ci ON ci.id = a.content_item_id
                    JOIN draft_versions dv ON dv.id = a.version_id AND dv.content_hash = a.content_hash
                    LEFT JOIN publication_plans pp
                        ON pp.content_item_id = ci.id
                        AND pp.version_id = a.version_id
                        AND pp.status = 'published'
                    WHERE
                        (ci.status = 'approved' AND ci.current_version_id = a.version_id)
                        OR pp.id IS NOT NULL
                )
                SELECT content_item_id, title, body, approved_at
                FROM candidates
                WHERE item_rank = 1
                ORDER BY approved_at DESC
                LIMIT ?
                """,
                (max_examples,),
            ).fetchall()
        if profile_row is None:  # pragma: no cover - protected by initialize()
            raise WorkflowError("The default writing profile is missing.")
        memory = AuthorMemory.model_validate_json(memory_row["payload"]) if memory_row else AuthorMemory()
        return WritingContext(
            past_post_topics=[{"title": post.title, "topics": post.topics}
                              for post in memory.past_posts if post.use_as_example],
            author_memory=memory.model_copy(update={"past_posts": [
                post for post in memory.past_posts if post.use_as_example
            ][:max_examples]}),
            profile=WritingProfile(
                style_instructions=profile_row["style_instructions"],
                target_audience=profile_row["target_audience"],
                language=profile_row["language"],
                updated_at=datetime.fromisoformat(profile_row["updated_at"]),
            ),
            approved_examples=[
                WritingExample(
                    content_item_id=row["content_item_id"],
                    title=row["title"],
                    body=row["body"],
                    approved_at=datetime.fromisoformat(row["approved_at"]),
                )
                for row in example_rows
            ],
        )

    def export_workspace(self) -> WorkspaceExport:
        profile = self.get_writing_context(max_examples=0).profile
        with self._connect() as connection:
            item_rows = connection.execute("SELECT id FROM content_items ORDER BY created_at, id").fetchall()
            items = [self._get_content_item(connection, row["id"]) for row in item_rows]
        return WorkspaceExport(exported_at=_now(), writing_profile=profile, content_items=items,
                               author_memory=self.get_author_memory())

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
    ) -> ContentItemDetail:
        payload = {
            "content_item_id": content_item_id,
            "impressions": impressions,
            "reactions": reactions,
            "comments": comments,
            "reposts": reposts,
            "notes": notes,
        }
        with self._connect(write=True) as connection:
            replay = self._replay(
                connection,
                "record_performance_snapshot",
                idempotency_key,
                payload,
                ContentItemDetail,
            )
            if replay is not None:
                return replay
            current = self._get_content_item(connection, content_item_id)
            if (
                current.publication_plan is None
                or current.publication_plan.status != PublicationPlanStatus.PUBLISHED
            ):
                raise ConflictError("Performance can be recorded only after publication is confirmed.")
            timestamp = _now().isoformat()
            snapshot_id = uuid4().hex
            connection.execute(
                """
                INSERT INTO performance_snapshots
                    (id, content_item_id, publication_plan_id, impressions, reactions, comments, reposts, notes,
                     recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    content_item_id,
                    current.publication_plan.id,
                    impressions,
                    reactions,
                    comments,
                    reposts,
                    notes,
                    timestamp,
                ),
            )
            connection.execute("UPDATE content_items SET updated_at = ? WHERE id = ?", (timestamp, content_item_id))
            self._record_event(
                connection,
                content_item_id=content_item_id,
                event_type="performance_snapshot_recorded",
                details={"snapshot_id": snapshot_id},
                timestamp=timestamp,
            )
            result = self._get_content_item(connection, content_item_id)
            self._remember(connection, "record_performance_snapshot", idempotency_key, payload, result)
            return result

    @staticmethod
    def _record_event(
        connection: Any,
        *,
        content_item_id: str | None,
        event_type: str,
        details: dict[str, str | int | bool | None],
        timestamp: str,
    ) -> None:
        # Windows clocks can return the same instant for successive transactions.
        # Mutations hold the workspace write lock, so this also orders API/MCP events.
        previous = connection.execute("SELECT MAX(created_at) AS latest FROM workflow_events").fetchone()
        if previous and previous["latest"]:
            latest = datetime.fromisoformat(previous["latest"])
            if datetime.fromisoformat(timestamp) <= latest:
                timestamp = (latest + timedelta(microseconds=1)).isoformat()
        connection.execute(
            """
            INSERT INTO workflow_events (id, content_item_id, event_type, details_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                content_item_id,
                event_type,
                json.dumps(details, ensure_ascii=False, sort_keys=True),
                timestamp,
            ),
        )

    def _cancel_active_plan(
        self,
        connection: Any,
        content_item_id: str,
        timestamp: str,
    ) -> None:
        plan = connection.execute(
            """
            SELECT id FROM publication_plans
            WHERE content_item_id = ? AND status IN (?, ?)
            """,
            (
                content_item_id,
                PublicationPlanStatus.PLANNED.value,
                PublicationPlanStatus.SCHEDULED_EXTERNALLY.value,
            ),
        ).fetchone()
        if plan is None:
            return
        connection.execute(
            "UPDATE publication_plans SET status = ?, updated_at = ? WHERE id = ?",
            (PublicationPlanStatus.CANCELLED.value, timestamp, plan["id"]),
        )
        self._record_event(
            connection,
            content_item_id=content_item_id,
            event_type="publication_plan_cancelled",
            details={"plan_id": plan["id"], "reason": "content_changed"},
            timestamp=timestamp,
        )

    @staticmethod
    def _require_plan(
        connection: Any,
        content_item_id: str,
        plan_id: str,
    ) -> Any:
        plan = connection.execute(
            "SELECT * FROM publication_plans WHERE id = ? AND content_item_id = ?",
            (plan_id, content_item_id),
        ).fetchone()
        if plan is None:
            raise NotFoundError(f"Publication plan '{plan_id}' was not found for this content item.")
        return plan

    def _get_content_item(self, connection: Any, content_item_id: str) -> ContentItemDetail:
        row = connection.execute("SELECT * FROM content_items WHERE id = ?", (content_item_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Content item '{content_item_id}' was not found.")
        source_rows = connection.execute(
            "SELECT * FROM source_references WHERE content_item_id = ? ORDER BY created_at, id",
            (content_item_id,),
        ).fetchall()
        version_rows = connection.execute(
            "SELECT * FROM draft_versions WHERE content_item_id = ? ORDER BY version_number",
            (content_item_id,),
        ).fetchall()
        feedback_rows = connection.execute(
            "SELECT * FROM review_feedback WHERE content_item_id = ? ORDER BY created_at, id",
            (content_item_id,),
        ).fetchall()
        plan_row = connection.execute(
            "SELECT * FROM publication_plans WHERE content_item_id = ?",
            (content_item_id,),
        ).fetchone()
        event_rows = connection.execute(
            "SELECT * FROM workflow_events WHERE content_item_id = ? ORDER BY created_at DESC, id DESC",
            (content_item_id,),
        ).fetchall()
        performance_rows = connection.execute(
            "SELECT * FROM performance_snapshots WHERE content_item_id = ? ORDER BY recorded_at DESC, id DESC",
            (content_item_id,),
        ).fetchall()
        approval_row = None
        if row["current_version_id"] is not None:
            approval_row = connection.execute(
                """
                SELECT a.* FROM approvals a
                JOIN draft_versions dv ON dv.id = a.version_id AND dv.content_hash = a.content_hash
                WHERE a.content_item_id = ? AND a.version_id = ?
                ORDER BY a.approved_at DESC LIMIT 1
                """,
                (content_item_id, row["current_version_id"]),
            ).fetchone()
        summary = self._summary_from_row(row)
        return ContentItemDetail(
            **summary.model_dump(),
            raw_input=row["raw_input"],
            sources=[
                SourceReference(
                    id=source["id"],
                    url=source["url"],
                    title=source["title"],
                    note=source["note"],
                    created_at=datetime.fromisoformat(source["created_at"]),
                )
                for source in source_rows
            ],
            versions=[
                DraftVersion(
                    id=version["id"],
                    content_item_id=version["content_item_id"],
                    version_number=version["version_number"],
                    body=version["body"],
                    content_hash=version["content_hash"],
                    change_summary=version["change_summary"],
                    created_at=datetime.fromisoformat(version["created_at"]),
                )
                for version in version_rows
            ],
            feedback=[
                ReviewFeedback(
                    id=feedback["id"],
                    content_item_id=feedback["content_item_id"],
                    version_id=feedback["version_id"],
                    message=feedback["message"],
                    created_at=datetime.fromisoformat(feedback["created_at"]),
                )
                for feedback in feedback_rows
            ],
            active_approval=(
                Approval(
                    id=approval_row["id"],
                    content_item_id=approval_row["content_item_id"],
                    version_id=approval_row["version_id"],
                    content_hash=approval_row["content_hash"],
                    approved_at=datetime.fromisoformat(approval_row["approved_at"]),
                )
                if approval_row is not None and row["status"] == ContentStatus.APPROVED.value
                else None
            ),
            publication_plan=(
                PublicationPlan(
                    id=plan_row["id"],
                    content_item_id=plan_row["content_item_id"],
                    version_id=plan_row["version_id"],
                    planned_for=datetime.fromisoformat(plan_row["planned_for"]),
                    timezone=plan_row["timezone"],
                    status=PublicationPlanStatus(plan_row["status"]),
                    external_confirmation_note=plan_row["external_confirmation_note"],
                    created_at=datetime.fromisoformat(plan_row["created_at"]),
                    updated_at=datetime.fromisoformat(plan_row["updated_at"]),
                )
                if plan_row is not None
                else None
            ),
            events=[
                WorkflowEvent(
                    id=event["id"],
                    content_item_id=event["content_item_id"],
                    event_type=event["event_type"],
                    details=json.loads(event["details_json"]),
                    created_at=datetime.fromisoformat(event["created_at"]),
                )
                for event in event_rows
            ],
            performance_snapshots=[
                PerformanceSnapshot(
                    id=snapshot["id"],
                    content_item_id=snapshot["content_item_id"],
                    publication_plan_id=snapshot["publication_plan_id"],
                    impressions=snapshot["impressions"],
                    reactions=snapshot["reactions"],
                    comments=snapshot["comments"],
                    reposts=snapshot["reposts"],
                    notes=snapshot["notes"],
                    recorded_at=datetime.fromisoformat(snapshot["recorded_at"]),
                )
                for snapshot in performance_rows
            ],
        )

    @staticmethod
    def _summary_from_row(row: Any) -> ContentItemSummary:
        return ContentItemSummary(
            id=row["id"],
            title=row["title"],
            source_kind=ContentSourceKind(row["source_kind"]),
            status=ContentStatus(row["status"]),
            current_version_id=row["current_version_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SQLiteContentRepository(SqlContentRepository):
    def __init__(self, database_path: Path | str) -> None:
        super().__init__(database_path)


class PostgresContentRepository(SqlContentRepository):
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("PostgresContentRepository requires a PostgreSQL connection URL.")
        super().__init__(database_url)
