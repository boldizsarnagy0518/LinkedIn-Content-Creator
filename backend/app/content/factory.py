from pathlib import Path

from app.content.ports import ContentRepository
from app.content.repository import PostgresContentRepository, SQLiteContentRepository


def create_content_repository(
    *,
    database_path: Path | str,
    database_url: str | None = None,
) -> ContentRepository:
    if database_url:
        return PostgresContentRepository(database_url)
    return SQLiteContentRepository(database_path)
