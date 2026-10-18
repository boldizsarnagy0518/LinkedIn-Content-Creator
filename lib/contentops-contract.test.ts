import { describe, expect, it } from "vitest";
import {
  normalizeCapturedContentItem,
  normalizeContentItemDetail,
  normalizeContentItemList,
  normalizeContentOpsError,
  normalizeWritingProfile
} from "./contentops-contract";

describe("normalizeCapturedContentItem", () => {
  it("normalizes the Python content workflow contract", () => {
    const item = normalizeCapturedContentItem({
      id: "item-1",
      title: "A durable idea",
      raw_input: "A rough but useful thought.",
      source_kind: "idea",
      status: "captured",
      created_at: "2026-08-04T12:00:00Z",
      updated_at: "2026-08-04T12:00:00Z"
    });

    expect(item).toMatchObject({
      id: "item-1",
      rawIdea: "A rough but useful thought.",
      sourceKind: "idea",
      status: "captured"
    });
  });

  it("rejects an unknown workflow status", () => {
    expect(() =>
      normalizeCapturedContentItem({
        id: "item-1",
        title: "A durable idea",
        raw_input: "A rough but useful thought.",
        source_kind: "idea",
        status: "published",
        created_at: "2026-08-04T12:00:00Z",
        updated_at: "2026-08-04T12:00:00Z"
      })
    ).toThrow(/status/i);
  });
});

describe("normalizeContentOpsError", () => {
  it("keeps the backend error and request id", () => {
    expect(
      normalizeContentOpsError(
        { error: "Duplicate request", code: "content_workflow_conflict", request_id: "request-1" },
        "fallback"
      )
    ).toEqual({
      error: "Duplicate request",
      code: "content_workflow_conflict",
      requestId: "request-1"
    });
  });
});

describe("normalizeContentItemList", () => {
  it("normalizes durable inbox summaries", () => {
    const list = normalizeContentItemList({
      items: [
        {
          id: "item-1",
          title: "Inbox item",
          source_kind: "idea",
          status: "captured",
          current_version_id: null,
          created_at: "2026-08-04T12:00:00Z",
          updated_at: "2026-08-04T12:00:00Z"
        }
      ],
      count: 1
    });

    expect(list.count).toBe(1);
    expect(list.items[0]).toMatchObject({ id: "item-1", sourceKind: "idea", status: "captured" });
  });
});

describe("normalizeContentItemDetail", () => {
  it("normalizes version, approval, publication, and audit state", () => {
    const detail = normalizeContentItemDetail({
      id: "item-1",
      title: "Reviewable item",
      raw_input: "Raw idea",
      source_kind: "idea",
      status: "approved",
      current_version_id: "version-1",
      created_at: "2026-08-04T12:00:00Z",
      updated_at: "2026-08-04T13:00:00Z",
      sources: [],
      versions: [{
        id: "version-1",
        content_item_id: "item-1",
        version_number: 1,
        body: "Reviewed copy",
        content_hash: "a".repeat(64),
        change_summary: null,
        created_at: "2026-08-04T12:30:00Z"
      }],
      feedback: [],
      active_approval: {
        id: "approval-1",
        content_item_id: "item-1",
        version_id: "version-1",
        content_hash: "a".repeat(64),
        approved_at: "2026-08-04T13:00:00Z"
      },
      publication_plan: {
        id: "plan-1",
        content_item_id: "item-1",
        version_id: "version-1",
        planned_for: "2026-08-10T07:00:00Z",
        timezone: "Europe/Budapest",
        status: "planned",
        external_confirmation_note: null,
        created_at: "2026-08-04T13:01:00Z",
        updated_at: "2026-08-04T13:01:00Z"
      },
      events: [{
        id: "event-1",
        content_item_id: "item-1",
        event_type: "publication_planned",
        details: { plan_id: "plan-1" },
        created_at: "2026-08-04T13:01:00Z"
      }],
      performance_snapshots: [{
        id: "snapshot-1",
        content_item_id: "item-1",
        publication_plan_id: "plan-1",
        impressions: 1000,
        reactions: 30,
        comments: 4,
        reposts: 2,
        notes: "24-hour snapshot",
        recorded_at: "2026-08-11T13:01:00Z"
      }]
    });

    expect(detail.currentVersionId).toBe("version-1");
    expect(detail.activeApproval?.contentHash).toBe("a".repeat(64));
    expect(detail.publicationPlan?.status).toBe("planned");
    expect(detail.events[0].eventType).toBe("publication_planned");
    expect(detail.performanceSnapshots[0].impressions).toBe(1000);
  });
});

describe("normalizeWritingProfile", () => {
  it("normalizes reusable writing preferences", () => {
    expect(normalizeWritingProfile({
      style_instructions: "Be concrete.",
      target_audience: null,
      language: "hu",
      updated_at: "2026-08-04T12:00:00Z"
    })).toMatchObject({ styleInstructions: "Be concrete.", targetAudience: null, language: "hu" });
  });
});
