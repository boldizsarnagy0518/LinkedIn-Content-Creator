export type ApiErrorResponse = {
  error: string;
  code: string;
  requestId: string;
};

export type ContentWorkflowStatus = "captured" | "draft" | "changes_requested" | "approved" | "archived";
export type ContentSourceKind = "idea" | "research";
export type PublicationPlanStatus = "planned" | "scheduled_externally" | "published" | "cancelled";

export type ContentItemSummary = {
  id: string;
  title: string;
  sourceKind: ContentSourceKind;
  status: ContentWorkflowStatus;
  currentVersionId: string | null;
  createdAt: string;
  updatedAt: string;
};

export type SourceReference = {
  id: string;
  url: string;
  title: string | null;
  note: string | null;
  createdAt: string;
};

export type WorkflowDraftVersion = {
  id: string;
  contentItemId: string;
  versionNumber: number;
  body: string;
  contentHash: string;
  changeSummary: string | null;
  createdAt: string;
};

export type ReviewFeedback = {
  id: string;
  contentItemId: string;
  versionId: string;
  message: string;
  createdAt: string;
};

export type WorkflowApproval = {
  id: string;
  contentItemId: string;
  versionId: string;
  contentHash: string;
  approvedAt: string;
};

export type PublicationPlan = {
  id: string;
  contentItemId: string;
  versionId: string;
  plannedFor: string;
  timezone: string;
  status: PublicationPlanStatus;
  externalConfirmationNote: string | null;
  createdAt: string;
  updatedAt: string;
};

export type WorkflowEvent = {
  id: string;
  contentItemId: string | null;
  eventType: string;
  details: Record<string, string | number | boolean | null>;
  createdAt: string;
};

export type PerformanceSnapshot = {
  id: string;
  contentItemId: string;
  publicationPlanId: string;
  impressions: number | null;
  reactions: number | null;
  comments: number | null;
  reposts: number | null;
  notes: string | null;
  recordedAt: string;
};

export type ContentItemDetail = ContentItemSummary & {
  rawInput: string;
  sources: SourceReference[];
  versions: WorkflowDraftVersion[];
  feedback: ReviewFeedback[];
  activeApproval: WorkflowApproval | null;
  publicationPlan: PublicationPlan | null;
  events: WorkflowEvent[];
  performanceSnapshots: PerformanceSnapshot[];
};

export type WritingProfile = {
  styleInstructions: string;
  targetAudience: string | null;
  language: string;
  updatedAt: string;
};

export type AuthorMemory = {
  background: string;
  past_posts: { title: string; body: string; topics: string; use_as_example: boolean }[];
  revision: string;
};

export type CapturedContentItem = ContentItemSummary & {
  rawIdea: string;
};

export type ContentItemListResponse = {
  items: ContentItemSummary[];
  count: number;
};

export type WorkspaceExport = {
  exportedAt: string;
  writingProfile: WritingProfile;
  contentItems: ContentItemDetail[];
};
