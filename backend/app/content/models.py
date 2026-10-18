from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ContentSourceKind(StrEnum):
    IDEA = "idea"
    RESEARCH = "research"


class ContentStatus(StrEnum):
    CAPTURED = "captured"
    DRAFT = "draft"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    ARCHIVED = "archived"


class PublicationPlanStatus(StrEnum):
    PLANNED = "planned"
    SCHEDULED_EXTERNALLY = "scheduled_externally"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class SourceReference(BaseModel):
    id: str
    url: str
    title: str | None = None
    note: str | None = None
    created_at: datetime


class DraftVersion(BaseModel):
    id: str
    content_item_id: str
    version_number: int = Field(ge=1)
    body: str
    content_hash: str
    change_summary: str | None = None
    created_at: datetime


class ReviewFeedback(BaseModel):
    id: str
    content_item_id: str
    version_id: str
    message: str
    created_at: datetime


class Approval(BaseModel):
    id: str
    content_item_id: str
    version_id: str
    content_hash: str
    approved_at: datetime


class PublicationPlan(BaseModel):
    id: str
    content_item_id: str
    version_id: str
    planned_for: datetime
    timezone: str
    status: PublicationPlanStatus
    external_confirmation_note: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowEvent(BaseModel):
    id: str
    content_item_id: str | None
    event_type: str
    details: dict[str, str | int | bool | None] = Field(default_factory=dict)
    created_at: datetime


class PerformanceSnapshot(BaseModel):
    id: str
    content_item_id: str
    publication_plan_id: str
    impressions: int | None = Field(default=None, ge=0)
    reactions: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    reposts: int | None = Field(default=None, ge=0)
    notes: str | None
    recorded_at: datetime


class ContentItemSummary(BaseModel):
    id: str
    title: str
    source_kind: ContentSourceKind
    status: ContentStatus
    current_version_id: str | None
    created_at: datetime
    updated_at: datetime


class ContentItemDetail(ContentItemSummary):
    raw_input: str
    sources: list[SourceReference]
    versions: list[DraftVersion]
    feedback: list[ReviewFeedback]
    active_approval: Approval | None
    publication_plan: PublicationPlan | None = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    performance_snapshots: list[PerformanceSnapshot] = Field(default_factory=list)


class ContentItemList(BaseModel):
    items: list[ContentItemSummary]
    count: int = Field(ge=0)


class WritingProfile(BaseModel):
    style_instructions: str
    target_audience: str | None
    language: str
    updated_at: datetime


class WritingExample(BaseModel):
    content_item_id: str
    title: str
    body: str
    approved_at: datetime


class PastPost(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=5000)
    topics: str = Field(default="", max_length=500)
    use_as_example: bool = True


class AuthorMemory(BaseModel):
    background: str = Field(default="", max_length=12000)
    past_posts: list[PastPost] = Field(default_factory=list, max_length=50)
    revision: str = Field(default="empty", min_length=1, max_length=64)


class WritingContext(BaseModel):
    profile: WritingProfile
    approved_examples: list[WritingExample]
    author_memory: AuthorMemory = Field(default_factory=AuthorMemory)
    past_post_topics: list[dict[str, str]] = Field(default_factory=list)


class WorkspaceExport(BaseModel):
    exported_at: datetime
    writing_profile: WritingProfile
    content_items: list[ContentItemDetail]
    author_memory: AuthorMemory = Field(default_factory=AuthorMemory)
