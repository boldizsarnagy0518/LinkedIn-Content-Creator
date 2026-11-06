"""Copy a complete ContentOps workspace between repositories, for example local SQLite to Supabase Postgres."""

from typing import Any

from app.content.repository import ConflictError, SqlContentRepository

# Parents before children, so foreign keys hold at every insert.
TRANSFER_TABLES = (
    "content_items",
    "draft_versions",
    "source_references",
    "review_feedback",
    "approvals",
    "publication_plans",
    "performance_snapshots",
    "workflow_events",
    "writing_profiles",
    "author_memory",
    "idempotency_records",
)


def _columns(repository: SqlContentRepository, connection: Any, table: str) -> list[str]:
    if repository.database_url is not None:
        rows = connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = ? ORDER BY ordinal_position",
            (table,),
        ).fetchall()
        return [row["column_name"] for row in rows]
    return [row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]


def _count(connection: Any, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()["total"])


def count_rows(repository: SqlContentRepository) -> dict[str, int]:
    with repository._connect() as connection:
        return {table: _count(connection, table) for table in TRANSFER_TABLES}


def transfer_workspace(source: SqlContentRepository, target: SqlContentRepository) -> dict[str, int]:
    """Copy every row, keeping IDs, hashes, approvals and audit events intact.

    The target must hold no workspace data yet. Its default writing profile, created on first start, is
    replaced. The copy runs in one target transaction, so a failure leaves the target unchanged.
    """
    copied: dict[str, int] = {}
    with source._connect() as source_connection, target._connect(write=True) as target_connection:
        occupied = [
            table
            for table in TRANSFER_TABLES
            if table != "writing_profiles" and _count(target_connection, table) > 0
        ]
        if occupied:
            raise ConflictError(
                "The target workspace is not empty (" + ", ".join(occupied) + "). Nothing was copied."
            )
        target_connection.execute("DELETE FROM writing_profiles")
        for table in TRANSFER_TABLES:
            source_columns = _columns(source, source_connection, table)
            target_columns = set(_columns(target, target_connection, table))
            columns = [column for column in source_columns if column in target_columns]
            rows = source_connection.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
            if rows:
                placeholders = ", ".join("?" for _ in columns)
                target_connection.executemany(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                    [tuple(row[column] for column in columns) for row in rows],
                )
            copied[table] = len(rows)
    return copied
