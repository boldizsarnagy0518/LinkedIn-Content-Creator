from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.content.api_models import (
    ApproveDraftRequest,
    CaptureIdeaRequest,
    CaptureResearchRequest,
    ConfirmExternalScheduleRequest,
    MarkPublishedRequest,
    RecordPerformanceSnapshotRequest,
    RequestChangesRequest,
    SaveDraftVersionRequest,
    SetPublicationPlanRequest,
    UpdateAuthorMemoryRequest,
    UpdateWritingProfileRequest,
    WorkflowMutationRequest,
)
from app.content.dependencies import get_content_workflow_service
from app.content.models import (
    AuthorMemory,
    ContentItemDetail,
    ContentItemList,
    ContentStatus,
    WorkspaceExport,
    WritingProfile,
)
from app.content.service import ContentWorkflowService

router = APIRouter(prefix="/content-items", tags=["content workflow"])
profile_router = APIRouter(prefix="/writing-profile", tags=["writing profile"])
WorkflowService = Annotated[ContentWorkflowService, Depends(get_content_workflow_service)]


@router.post("/ideas", response_model=ContentItemDetail, status_code=status.HTTP_201_CREATED)
def capture_idea(
    request: CaptureIdeaRequest,
    response: Response,
    service: WorkflowService,
    x_request_id: Annotated[str | None, Header()] = None,
) -> ContentItemDetail:
    request_id = (x_request_id or "").strip()[:100] or uuid4().hex
    response.headers["X-Request-ID"] = request_id
    return service.capture_idea(
        raw_idea=request.raw_idea,
        idempotency_key=request.idempotency_key,
        title=request.title,
    )


@router.post("/research", response_model=ContentItemDetail, status_code=status.HTTP_201_CREATED)
def capture_research(request: CaptureResearchRequest, service: WorkflowService) -> ContentItemDetail:
    return service.capture_research(
        topic=request.topic,
        research_notes=request.research_notes,
        source_urls=request.source_urls,
        idempotency_key=request.idempotency_key,
    )


@router.get("/export", response_model=WorkspaceExport)
def export_workspace(service: WorkflowService) -> WorkspaceExport:
    return service.export_workspace()


@router.get("", response_model=ContentItemList)
def list_content_items(
    service: WorkflowService,
    status_filter: Annotated[ContentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ContentItemList:
    return service.list_content_items(status=status_filter, limit=limit)


@router.get("/{content_item_id}", response_model=ContentItemDetail)
def get_content_item(content_item_id: str, service: WorkflowService) -> ContentItemDetail:
    return service.get_content_item(content_item_id)


@router.post("/{content_item_id}/versions", response_model=ContentItemDetail)
def save_draft_version(
    content_item_id: str,
    request: SaveDraftVersionRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.save_draft_version(
        content_item_id=content_item_id,
        body=request.body,
        change_summary=request.change_summary,
        expected_current_version_id=request.expected_current_version_id,
        idempotency_key=request.idempotency_key,
    )


@router.post("/{content_item_id}/feedback", response_model=ContentItemDetail)
def request_changes(
    content_item_id: str,
    request: RequestChangesRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.request_changes(
        content_item_id=content_item_id,
        version_id=request.version_id,
        feedback=request.feedback,
        idempotency_key=request.idempotency_key,
    )


@router.post("/{content_item_id}/approval", response_model=ContentItemDetail)
def approve_draft(
    content_item_id: str,
    request: ApproveDraftRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.approve_draft(
        content_item_id=content_item_id,
        version_id=request.version_id,
        expected_content_hash=request.expected_content_hash,
        idempotency_key=request.idempotency_key,
    )


@router.post("/{content_item_id}/approval/revoke", response_model=ContentItemDetail)
def revoke_approval(
    content_item_id: str,
    request: WorkflowMutationRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.revoke_approval(content_item_id=content_item_id, idempotency_key=request.idempotency_key)


@router.post("/{content_item_id}/archive", response_model=ContentItemDetail)
def archive_content_item(
    content_item_id: str,
    request: WorkflowMutationRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.archive_content_item(content_item_id=content_item_id, idempotency_key=request.idempotency_key)


@router.put("/{content_item_id}/publication-plan", response_model=ContentItemDetail)
def set_publication_plan(
    content_item_id: str,
    request: SetPublicationPlanRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.set_publication_plan(
        content_item_id=content_item_id,
        version_id=request.version_id,
        planned_for=request.planned_for,
        timezone=request.timezone,
        idempotency_key=request.idempotency_key,
    )


@router.post("/{content_item_id}/publication-plan/confirm-external", response_model=ContentItemDetail)
def confirm_external_schedule(
    content_item_id: str,
    request: ConfirmExternalScheduleRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.confirm_external_schedule(
        content_item_id=content_item_id,
        plan_id=request.plan_id,
        confirmation_note=request.confirmation_note,
        idempotency_key=request.idempotency_key,
    )


@router.post("/{content_item_id}/publication-plan/mark-published", response_model=ContentItemDetail)
def mark_published(
    content_item_id: str,
    request: MarkPublishedRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.mark_published(
        content_item_id=content_item_id,
        plan_id=request.plan_id,
        confirmation_note=request.confirmation_note,
        idempotency_key=request.idempotency_key,
    )


@router.post("/{content_item_id}/performance-snapshots", response_model=ContentItemDetail)
def record_performance_snapshot(
    content_item_id: str,
    request: RecordPerformanceSnapshotRequest,
    service: WorkflowService,
) -> ContentItemDetail:
    return service.record_performance_snapshot(
        content_item_id=content_item_id,
        impressions=request.impressions,
        reactions=request.reactions,
        comments=request.comments,
        reposts=request.reposts,
        notes=request.notes,
        idempotency_key=request.idempotency_key,
    )


@profile_router.get("", response_model=WritingProfile)
def get_writing_profile(service: WorkflowService) -> WritingProfile:
    return service.get_writing_context(max_examples=0).profile


@profile_router.get("/memory", response_model=AuthorMemory)
def get_author_memory(service: WorkflowService) -> AuthorMemory:
    return service.get_author_memory()


@profile_router.put("/memory", response_model=AuthorMemory)
def update_author_memory(request: UpdateAuthorMemoryRequest, service: WorkflowService) -> AuthorMemory:
    return service.update_author_memory(request.memory, request.idempotency_key)


@profile_router.put("", response_model=WritingProfile)
def update_writing_profile(
    request: UpdateWritingProfileRequest,
    service: WorkflowService,
) -> WritingProfile:
    return service.update_writing_profile(
        style_instructions=request.style_instructions,
        target_audience=request.target_audience,
        language=request.language,
        idempotency_key=request.idempotency_key,
    )
