from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.auth import Identity, require_identity
from app.config import settings
from app.content.factory import create_content_repository
from app.content.service import ContentWorkflowService


@lru_cache(maxsize=1)
def _get_content_workflow_service() -> ContentWorkflowService:
    """Return the application service backed by the same database as the MCP server."""
    repository = create_content_repository(
        database_path=settings.contentops_db_path,
        database_url=settings.contentops_database_url,
    )
    return ContentWorkflowService(repository)


def get_content_workflow_service(
    _: Annotated[Identity, Depends(require_identity)],
) -> ContentWorkflowService:
    return _get_content_workflow_service()
