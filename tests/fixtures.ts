import type { ContentItemDetail } from "@/types/content";

export function item(id = "idea-1", bodies: string[] = []): ContentItemDetail {
  const versions = bodies.map((body, i) => ({ id: `${id}-v${i + 1}`, contentItemId: id,
    versionNumber: i + 1, body, contentHash: String(i + 1).repeat(64), changeSummary: null,
    createdAt: "2026-09-08T10:00:00Z" }));
  return { id, title: `Ötlet ${id}`, sourceKind: "idea", status: versions.length ? "draft" : "captured",
    currentVersionId: versions.at(-1)?.id ?? null, rawInput: "Séta közben jutott eszembe.",
    createdAt: "2026-09-08T10:00:00Z", updatedAt: "2026-09-08T10:00:00Z",
    versions, sources: [], feedback: [], activeApproval: null, publicationPlan: null, events: [], performanceSnapshots: [] };
}
