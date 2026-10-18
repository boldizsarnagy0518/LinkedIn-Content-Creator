import type {
  ApiErrorResponse,
  CapturedContentItem,
  ContentItemDetail,
  ContentItemListResponse,
  ContentItemSummary,
  ContentSourceKind,
  ContentWorkflowStatus,
  PublicationPlanStatus,
  WritingProfile
} from "@/types/content";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(value: unknown, field: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`Backend contract error: ${field} must be a non-empty string`);
  }
  return value.trim();
}

function readOptionalString(value: unknown, field: string): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value !== "string") {
    throw new Error(`Backend contract error: ${field} must be a string or null`);
  }
  return value;
}

function readNumber(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Backend contract error: ${field} must be a number`);
  }
  return value;
}

function normalizeContentItemSummaryRecord(value: Record<string, unknown>): ContentItemSummary {
  const sourceKind = readString(value.source_kind ?? value.sourceKind, "source_kind") as ContentSourceKind;
  if (sourceKind !== "idea" && sourceKind !== "research") {
    throw new Error("Backend contract error: source_kind is invalid");
  }

  const status = readString(value.status, "status") as ContentWorkflowStatus;
  if (!["captured", "draft", "changes_requested", "approved", "archived"].includes(status)) {
    throw new Error("Backend contract error: content status is invalid");
  }

  return {
    id: readString(value.id, "id"),
    title: readString(value.title, "title"),
    sourceKind,
    status,
    currentVersionId: readOptionalString(value.current_version_id ?? value.currentVersionId, "current_version_id"),
    createdAt: readString(value.created_at ?? value.createdAt, "created_at"),
    updatedAt: readString(value.updated_at ?? value.updatedAt, "updated_at")
  };
}

export function normalizeContentItemDetail(value: unknown): ContentItemDetail {
  if (!isRecord(value)) {
    throw new Error("Backend contract error: content item detail must be an object");
  }
  const summary = normalizeContentItemSummaryRecord(value);
  if (!Array.isArray(value.sources) || !Array.isArray(value.versions) || !Array.isArray(value.feedback)) {
    throw new Error("Backend contract error: content item detail collections are invalid");
  }
  const events = value.events ?? [];
  if (!Array.isArray(events)) {
    throw new Error("Backend contract error: workflow events are invalid");
  }
  const performanceSnapshots = value.performance_snapshots ?? value.performanceSnapshots ?? [];
  if (!Array.isArray(performanceSnapshots)) {
    throw new Error("Backend contract error: performance snapshots are invalid");
  }

  const approvalValue = value.active_approval ?? value.activeApproval;
  const planValue = value.publication_plan ?? value.publicationPlan;

  return {
    ...summary,
    rawInput: readString(value.raw_input ?? value.rawInput, "raw_input"),
    sources: value.sources.map((source, index) => {
      if (!isRecord(source)) throw new Error(`Backend contract error: sources[${index}] is invalid`);
      return {
        id: readString(source.id, `sources[${index}].id`),
        url: readString(source.url, `sources[${index}].url`),
        title: readOptionalString(source.title, `sources[${index}].title`),
        note: readOptionalString(source.note, `sources[${index}].note`),
        createdAt: readString(source.created_at ?? source.createdAt, `sources[${index}].created_at`)
      };
    }),
    versions: value.versions.map((version, index) => {
      if (!isRecord(version)) throw new Error(`Backend contract error: versions[${index}] is invalid`);
      return {
        id: readString(version.id, `versions[${index}].id`),
        contentItemId: readString(version.content_item_id ?? version.contentItemId, `versions[${index}].content_item_id`),
        versionNumber: readNumber(version.version_number ?? version.versionNumber, `versions[${index}].version_number`),
        body: readString(version.body, `versions[${index}].body`),
        contentHash: readString(version.content_hash ?? version.contentHash, `versions[${index}].content_hash`),
        changeSummary: readOptionalString(version.change_summary ?? version.changeSummary, `versions[${index}].change_summary`),
        createdAt: readString(version.created_at ?? version.createdAt, `versions[${index}].created_at`)
      };
    }),
    feedback: value.feedback.map((feedback, index) => {
      if (!isRecord(feedback)) throw new Error(`Backend contract error: feedback[${index}] is invalid`);
      return {
        id: readString(feedback.id, `feedback[${index}].id`),
        contentItemId: readString(feedback.content_item_id ?? feedback.contentItemId, `feedback[${index}].content_item_id`),
        versionId: readString(feedback.version_id ?? feedback.versionId, `feedback[${index}].version_id`),
        message: readString(feedback.message, `feedback[${index}].message`),
        createdAt: readString(feedback.created_at ?? feedback.createdAt, `feedback[${index}].created_at`)
      };
    }),
    activeApproval: isRecord(approvalValue)
      ? {
          id: readString(approvalValue.id, "active_approval.id"),
          contentItemId: readString(approvalValue.content_item_id ?? approvalValue.contentItemId, "active_approval.content_item_id"),
          versionId: readString(approvalValue.version_id ?? approvalValue.versionId, "active_approval.version_id"),
          contentHash: readString(approvalValue.content_hash ?? approvalValue.contentHash, "active_approval.content_hash"),
          approvedAt: readString(approvalValue.approved_at ?? approvalValue.approvedAt, "active_approval.approved_at")
        }
      : null,
    publicationPlan: isRecord(planValue)
      ? {
          id: readString(planValue.id, "publication_plan.id"),
          contentItemId: readString(planValue.content_item_id ?? planValue.contentItemId, "publication_plan.content_item_id"),
          versionId: readString(planValue.version_id ?? planValue.versionId, "publication_plan.version_id"),
          plannedFor: readString(planValue.planned_for ?? planValue.plannedFor, "publication_plan.planned_for"),
          timezone: readString(planValue.timezone, "publication_plan.timezone"),
          status: readPublicationPlanStatus(planValue.status),
          externalConfirmationNote: readOptionalString(
            planValue.external_confirmation_note ?? planValue.externalConfirmationNote,
            "publication_plan.external_confirmation_note"
          ),
          createdAt: readString(planValue.created_at ?? planValue.createdAt, "publication_plan.created_at"),
          updatedAt: readString(planValue.updated_at ?? planValue.updatedAt, "publication_plan.updated_at")
        }
      : null,
    events: events.map((event, index) => {
      if (!isRecord(event) || !isRecord(event.details)) {
        throw new Error(`Backend contract error: events[${index}] is invalid`);
      }
      return {
        id: readString(event.id, `events[${index}].id`),
        contentItemId: readOptionalString(event.content_item_id ?? event.contentItemId, `events[${index}].content_item_id`),
        eventType: readString(event.event_type ?? event.eventType, `events[${index}].event_type`),
        details: event.details as Record<string, string | number | boolean | null>,
        createdAt: readString(event.created_at ?? event.createdAt, `events[${index}].created_at`)
      };
    }),
    performanceSnapshots: performanceSnapshots.map((snapshot, index) => {
      if (!isRecord(snapshot)) {
        throw new Error(`Backend contract error: performance_snapshots[${index}] is invalid`);
      }
      return {
        id: readString(snapshot.id, `performance_snapshots[${index}].id`),
        contentItemId: readString(
          snapshot.content_item_id ?? snapshot.contentItemId,
          `performance_snapshots[${index}].content_item_id`
        ),
        publicationPlanId: readString(
          snapshot.publication_plan_id ?? snapshot.publicationPlanId,
          `performance_snapshots[${index}].publication_plan_id`
        ),
        impressions: readOptionalNumber(snapshot.impressions, `performance_snapshots[${index}].impressions`),
        reactions: readOptionalNumber(snapshot.reactions, `performance_snapshots[${index}].reactions`),
        comments: readOptionalNumber(snapshot.comments, `performance_snapshots[${index}].comments`),
        reposts: readOptionalNumber(snapshot.reposts, `performance_snapshots[${index}].reposts`),
        notes: readOptionalString(snapshot.notes, `performance_snapshots[${index}].notes`),
        recordedAt: readString(
          snapshot.recorded_at ?? snapshot.recordedAt,
          `performance_snapshots[${index}].recorded_at`
        )
      };
    })
  };
}

function readOptionalNumber(value: unknown, field: string): number | null {
  if (value === null || value === undefined) return null;
  return readNumber(value, field);
}

function readPublicationPlanStatus(value: unknown): PublicationPlanStatus {
  const status = readString(value, "publication_plan.status") as PublicationPlanStatus;
  if (!["planned", "scheduled_externally", "published", "cancelled"].includes(status)) {
    throw new Error("Backend contract error: publication plan status is invalid");
  }
  return status;
}

export function normalizeWritingProfile(value: unknown): WritingProfile {
  if (!isRecord(value)) throw new Error("Backend contract error: writing profile must be an object");
  return {
    styleInstructions: readString(value.style_instructions ?? value.styleInstructions, "style_instructions"),
    targetAudience: readOptionalString(value.target_audience ?? value.targetAudience, "target_audience"),
    language: readString(value.language, "language"),
    updatedAt: readString(value.updated_at ?? value.updatedAt, "updated_at")
  };
}

export function normalizeContentItemSummary(value: unknown): ContentItemSummary {
  if (!isRecord(value)) {
    throw new Error("Backend contract error: content item must be an object");
  }
  return normalizeContentItemSummaryRecord(value);
}

export function normalizeCapturedContentItem(value: unknown): CapturedContentItem {
  if (!isRecord(value)) {
    throw new Error("Backend contract error: content item must be an object");
  }

  const summary = normalizeContentItemSummaryRecord(value);

  return {
    ...summary,
    rawIdea: readString(value.raw_input ?? value.rawIdea, "raw_input"),
  };
}

export function normalizeContentItemList(value: unknown): ContentItemListResponse {
  if (!isRecord(value) || !Array.isArray(value.items) || typeof value.count !== "number" || value.count < 0) {
    throw new Error("Backend contract error: content item list is invalid");
  }

  return {
    items: value.items.map(normalizeContentItemSummary),
    count: value.count
  };
}

export function normalizeContentOpsError(value: unknown, fallbackRequestId: string): ApiErrorResponse {
  if (!isRecord(value)) {
    return {
      error: "The content workflow returned an unexpected error.",
      code: "unexpected_backend_error",
      requestId: fallbackRequestId
    };
  }

  return {
    error: typeof value.error === "string" ? value.error : "The content workflow could not complete the request.",
    code: typeof value.code === "string" ? value.code : "content_workflow_error",
    requestId:
      typeof value.request_id === "string"
        ? value.request_id
        : typeof value.requestId === "string"
          ? value.requestId
          : fallbackRequestId
  };
}
