// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import * as api from "@/lib/contentops-api";
import { useContentOpsWorkspace } from "@/app/_hooks/use-contentops-workspace";
import { item } from "./fixtures";

vi.mock("@/lib/contentops-api", () => ({
  getWritingProfile: vi.fn(), listContentItems: vi.fn(), getContentItem: vi.fn(), captureIdea: vi.fn(),
  captureResearch: vi.fn(), updateWritingProfile: vi.fn()
}));

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getWritingProfile).mockResolvedValue({ styleInstructions: "Konkrétan", language: "hu", targetAudience: null, updatedAt: "2026-09-08T10:00:00Z" });
  vi.mocked(api.listContentItems).mockResolvedValue({ items: [item()], count: 1 });
  vi.mocked(api.getContentItem).mockImplementation(async (id) => item(id));
});
afterEach(cleanup);

it("does not get stuck when the current filter is selected again", async () => {
  const hook = renderHook(() => useContentOpsWorkspace());
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  act(() => hook.result.current.setFilter("active"));
  expect(hook.result.current.loading).toBe(false);
  expect(api.listContentItems).toHaveBeenCalledTimes(1);
});

it("ignores a late response from a previously selected document", async () => {
  const hook = renderHook(() => useContentOpsWorkspace());
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  let resolveOld!: (value: ReturnType<typeof item>) => void;
  vi.mocked(api.getContentItem).mockImplementation(async (id) => id === "old" ? new Promise((resolve) => { resolveOld = resolve; }) : item(id));
  let oldRequest!: Promise<void>;
  act(() => { oldRequest = hook.result.current.selectItem("old"); });
  await waitFor(() => expect(resolveOld).toBeTypeOf("function"));
  await act(async () => { await hook.result.current.selectItem("new"); });
  await act(async () => { resolveOld(item("old")); await oldRequest; });
  expect(hook.result.current.detail?.id).toBe("new");
});

it("refreshes an MCP-created draft when the window regains focus", async () => {
  const hook = renderHook(() => useContentOpsWorkspace());
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  vi.mocked(api.getContentItem).mockResolvedValue(item("idea-1", ["Host által mentett szöveg"]));
  act(() => window.dispatchEvent(new Event("focus")));
  await waitFor(() => expect(hook.result.current.detail?.versions[0]?.body).toBe("Host által mentett szöveg"));
});

it("does not report a successful capture as failed when the following refresh fails", async () => {
  const hook = renderHook(() => useContentOpsWorkspace());
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  vi.mocked(api.captureIdea).mockResolvedValue(item("saved"));
  vi.mocked(api.listContentItems).mockRejectedValue(new Error("Connection lost"));
  let result;
  await act(async () => { result = await hook.result.current.captureIdea("Új ötlet"); });
  expect(result).toMatchObject({ id: "saved" });
  expect(hook.result.current.detail?.id).toBe("saved");
  expect(api.captureIdea).toHaveBeenCalledTimes(1);
});
