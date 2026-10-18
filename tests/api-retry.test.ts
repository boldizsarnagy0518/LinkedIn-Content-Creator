import { afterEach, expect, it, vi } from "vitest";
import { captureIdea } from "@/lib/contentops-api";

afterEach(() => vi.unstubAllGlobals());

it("reuses the idempotency key after an uncertain timeout", async () => {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (_url: string, init: RequestInit) => {
    calls.push(JSON.parse(String(init.body)).idempotency_key);
    if (calls.length === 1) throw new TypeError("Connection lost after write");
    return new Response(JSON.stringify({ id: "saved", title: "Saved", source_kind: "idea", status: "captured",
      current_version_id: null, created_at: "2026-09-08", updated_at: "2026-09-08", raw_input: "Retry idea",
      sources: [], versions: [], feedback: [] }), { status: 200 });
  }));
  await expect(captureIdea("Retry idea")).rejects.toThrow();
  expect((await captureIdea("Retry idea")).id).toBe("saved");
  expect(calls[0]).toBe(calls[1]);
  await captureIdea("Retry idea");
  expect(calls[2]).not.toBe(calls[1]);
});
