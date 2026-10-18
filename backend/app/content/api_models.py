from datetime import datetime

from pydantic import Field

from app.content.models import AuthorMemory
from app.models import ApiModel


class UpdateAuthorMemoryRequest(ApiModel):
    memory: AuthorMemory
    idempotency_key: str = Field(min_length=8, max_length=128)


class CaptureIdeaRequest(ApiModel):
    raw_idea: str = Field(
        min_length=3,
        max_length=6000,
        description="The user's unpolished content idea.",
    )
    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        description="A stable key reused only when retrying the same capture request.",
    )
    title: str | None = Field(
        default=None,
        max_length=160,
        description="Optional working title; derived from the first line when omitted.",
    )


class CaptureResearchRequest(ApiModel):
    topic: str = Field(min_length=3, max_length=160)
    research_notes: str = Field(min_length=3, max_length=50_000)
    source_urls: list[str] = Field(min_length=1, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=128)


class SaveDraftVersionRequest(ApiModel):
    body: str = Field(min_length=1, max_length=50_000)
    idempotency_key: str = Field(min_length=8, max_length=128)
    change_summary: str | None = Field(default=None, max_length=2_000)
    expected_current_version_id: str | None = Field(
        default=None, min_length=1, max_length=128,
        description="Version read before editing; use 'source' for the first draft. Omission is legacy behavior.",
    )


class RequestChangesRequest(ApiModel):
    version_id: str = Field(min_length=1, max_length=128)
    feedback: str = Field(min_length=1, max_length=10_000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ApproveDraftRequest(ApiModel):
    version_id: str = Field(min_length=1, max_length=128)
    expected_content_hash: str = Field(min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=8, max_length=128)


class WorkflowMutationRequest(ApiModel):
    idempotency_key: str = Field(min_length=8, max_length=128)


class UpdateWritingProfileRequest(ApiModel):
    style_instructions: str = Field(min_length=1, max_length=10_000)
    target_audience: str | None = Field(default=None, max_length=2_000)
    language: str = Field(default="hu", min_length=2, max_length=16)
    idempotency_key: str = Field(min_length=8, max_length=128)


class SetPublicationPlanRequest(ApiModel):
    version_id: str = Field(min_length=1, max_length=128)
    planned_for: datetime
    timezone: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ConfirmExternalScheduleRequest(ApiModel):
    plan_id: str = Field(min_length=1, max_length=128)
    confirmation_note: str = Field(min_length=1, max_length=2_000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class MarkPublishedRequest(ApiModel):
    plan_id: str = Field(min_length=1, max_length=128)
    confirmation_note: str | None = Field(default=None, max_length=2_000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class RecordPerformanceSnapshotRequest(ApiModel):
    impressions: int | None = Field(default=None, ge=0)
    reactions: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    reposts: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2_000)
    idempotency_key: str = Field(min_length=8, max_length=128)
