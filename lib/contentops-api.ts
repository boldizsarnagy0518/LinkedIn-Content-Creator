import {
  normalizeContentItemDetail,
  normalizeContentItemList,
  normalizeContentOpsError,
  normalizeWritingProfile
} from "@/lib/contentops-contract";
import type {
  AuthorMemory,
  ContentItemDetail,
  ContentItemListResponse,
  ContentWorkflowStatus,
  WritingProfile
} from "@/types/content";

const API_ROOT = "/api/workflow";

function authorMemory(value: unknown): AuthorMemory {
  const memory = value as AuthorMemory | null;
  if (!memory || typeof memory.background !== "string" || typeof memory.revision !== "string" ||
      !Array.isArray(memory.past_posts) || !memory.past_posts.every((post) =>
        post && typeof post.title === "string" && typeof post.body === "string" &&
        typeof post.topics === "string" && typeof post.use_as_example === "boolean")) {
    throw new Error("A profiladatok nem olvashatók. Próbáld újra.");
  }
  return memory;
}

export async function getAuthorMemory(): Promise<AuthorMemory> {
  return authorMemory(await request("/writing-profile/memory"));
}

export async function saveAuthorMemory(memory: AuthorMemory): Promise<AuthorMemory> {
  return authorMemory(await request("/writing-profile/memory", { ...mutation({ memory }), method: "PUT" }));
}
const retryKeys = new Map<string, string>();

export class ContentOpsApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly requestId: string
  ) {
    super(message);
    this.name = "ContentOpsApiError";
  }
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  let retryIdentity: string | null = null;
  if (init?.body && typeof init.body === "string" && init.method !== "GET") {
    const body = JSON.parse(init.body) as Record<string, unknown>;
    const suppliedKey = typeof body.idempotency_key === "string" ? body.idempotency_key : crypto.randomUUID();
    delete body.idempotency_key;
    retryIdentity = `${path}:${JSON.stringify(body)}`;
    const key = retryKeys.get(retryIdentity) ?? suppliedKey;
    retryKeys.set(retryIdentity, key);
    init = { ...init, body: JSON.stringify({ ...body, idempotency_key: key }) };
  }
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (retryIdentity && response.status < 500) retryKeys.delete(retryIdentity);
    const error = normalizeContentOpsError(payload, response.headers.get("X-Request-ID") ?? crypto.randomUUID());
    throw new ContentOpsApiError(error.error, error.code, error.requestId);
  }
  if (retryIdentity) retryKeys.delete(retryIdentity);
  return payload;
}

function mutation(body: Record<string, unknown>, requestKey?: string): RequestInit {
  return { method: "POST", body: JSON.stringify({ ...body, idempotency_key: requestKey ?? crypto.randomUUID() }) };
}

export async function listContentItems(status?: ContentWorkflowStatus): Promise<ContentItemListResponse> {
  const query = new URLSearchParams({ limit: "100" });
  if (status) query.set("status", status);
  return normalizeContentItemList(await request(`/content-items?${query}`));
}

export async function getContentItem(contentItemId: string): Promise<ContentItemDetail> {
  return normalizeContentItemDetail(await request(`/content-items/${encodeURIComponent(contentItemId)}`));
}

export async function captureIdea(rawIdea: string, title?: string, requestKey?: string): Promise<ContentItemDetail> {
  return normalizeContentItemDetail(
    await request(
      "/content-items/ideas",
      mutation({ raw_idea: rawIdea, title: title?.trim() || null }, requestKey)
    )
  );
}

export async function captureResearch(
  topic: string,
  researchNotes: string,
  sourceUrls: string[],
  requestKey?: string
): Promise<ContentItemDetail> {
  return normalizeContentItemDetail(
    await request(
      "/content-items/research",
      mutation({ topic, research_notes: researchNotes, source_urls: sourceUrls }, requestKey)
    )
  );
}

export async function saveDraftVersion(
  contentItemId: string,
  body: string,
  changeSummary?: string,
  expectedCurrentVersionId?: string
): Promise<ContentItemDetail> {
  return normalizeContentItemDetail(
    await request(
      `/content-items/${encodeURIComponent(contentItemId)}/versions`,
      mutation({ body, change_summary: changeSummary?.trim() || null,
        expected_current_version_id: expectedCurrentVersionId ?? null })
    )
  );
}

export async function requestChanges(
  contentItemId: string,
  versionId: string,
  feedback: string
): Promise<ContentItemDetail> {
  return normalizeContentItemDetail(
    await request(
      `/content-items/${encodeURIComponent(contentItemId)}/feedback`,
      mutation({ version_id: versionId, feedback })
    )
  );
}

export async function approveDraft(contentItemId: string, versionId: string, contentHash: string) {
  return normalizeContentItemDetail(
    await request(
      `/content-items/${encodeURIComponent(contentItemId)}/approval`,
      mutation({ version_id: versionId, expected_content_hash: contentHash })
    )
  );
}

export async function revokeApproval(contentItemId: string) {
  return normalizeContentItemDetail(
    await request(`/content-items/${encodeURIComponent(contentItemId)}/approval/revoke`, mutation({}))
  );
}

export async function archiveContentItem(contentItemId: string) {
  return normalizeContentItemDetail(
    await request(`/content-items/${encodeURIComponent(contentItemId)}/archive`, mutation({}))
  );
}

export async function setPublicationPlan(
  contentItemId: string,
  versionId: string,
  plannedFor: string,
  timezone: string
) {
  return normalizeContentItemDetail(
    await request(`/content-items/${encodeURIComponent(contentItemId)}/publication-plan`, {
      ...mutation({ version_id: versionId, planned_for: plannedFor, timezone }),
      method: "PUT"
    })
  );
}

export async function confirmExternalSchedule(contentItemId: string, planId: string, note: string) {
  return normalizeContentItemDetail(
    await request(
      `/content-items/${encodeURIComponent(contentItemId)}/publication-plan/confirm-external`,
      mutation({ plan_id: planId, confirmation_note: note })
    )
  );
}

export async function markPublished(contentItemId: string, planId: string, note?: string) {
  return normalizeContentItemDetail(
    await request(
      `/content-items/${encodeURIComponent(contentItemId)}/publication-plan/mark-published`,
      mutation({ plan_id: planId, confirmation_note: note?.trim() || null })
    )
  );
}

export async function recordPerformance(
  contentItemId: string,
  metrics: {
    impressions?: number;
    reactions?: number;
    comments?: number;
    reposts?: number;
    notes?: string;
  }
) {
  return normalizeContentItemDetail(
    await request(
      `/content-items/${encodeURIComponent(contentItemId)}/performance-snapshots`,
      mutation({
        impressions: metrics.impressions ?? null,
        reactions: metrics.reactions ?? null,
        comments: metrics.comments ?? null,
        reposts: metrics.reposts ?? null,
        notes: metrics.notes?.trim() || null
      })
    )
  );
}

export async function getWritingProfile(): Promise<WritingProfile> {
  return normalizeWritingProfile(await request("/writing-profile"));
}

export async function updateWritingProfile(
  styleInstructions: string,
  targetAudience: string,
  language: string
): Promise<WritingProfile> {
  return normalizeWritingProfile(
    await request("/writing-profile", {
      ...mutation({
        style_instructions: styleInstructions,
        target_audience: targetAudience.trim() || null,
        language
      }),
      method: "PUT"
    })
  );
}
