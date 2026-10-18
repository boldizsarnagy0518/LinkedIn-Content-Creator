// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { DraftEditor } from "@/app/_components/draft-editor";
import { CaptureDialog } from "@/app/_components/capture-dialog";
import { WorkflowInspector } from "@/app/_components/workflow-inspector";
import { isWorkingCopy, readLocal, workspaceKey } from "@/lib/workspace-drafts";
import { item } from "./fixtures";

beforeEach(() => {
  localStorage.clear();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

function editorProps(detail = item("idea-1", ["Eredeti szöveg"])) {
  return { detail, account: "test-owner", busy: false, onSaveVersion: vi.fn().mockResolvedValue(null),
    onArchive: vi.fn(), onReviewState: vi.fn(), onHandoff: vi.fn(), onBack: vi.fn(), onCapture: vi.fn() };
}

describe("Working copies and review", () => {
  it("allows the first draft without a host model", async () => {
    const props = editorProps(item());
    render(<DraftEditor {...props} />);
    fireEvent.change(screen.getByLabelText("Poszt szövege"), { target: { value: "Saját első szöveg" } });
    fireEvent.click(screen.getByRole("button", { name: "Első draft mentése" }));
    await waitFor(() => expect(props.onSaveVersion).toHaveBeenCalledWith("Saját első szöveg", "", "source"));
    // A failed save must preserve the recovery copy.
    expect(readLocal(workspaceKey("test-owner", "draft:idea-1"), isWorkingCopy)?.body).toBe("Saját első szöveg");
  });

  it("preserves local edits across history navigation and incoming MCP versions", () => {
    const props = editorProps(item("idea-1", ["Első", "Második"]));
    const view = render(<DraftEditor {...props} />);
    fireEvent.change(screen.getByLabelText("Poszt szövege"), { target: { value: "Helyi szerkesztés" } });
    expect(props.onReviewState).toHaveBeenLastCalledWith(expect.objectContaining({ canReview: false, dirty: true }));
    fireEvent.click(screen.getByRole("button", { name: "v1" }));
    expect((screen.getByLabelText("Poszt szövege") as HTMLTextAreaElement).value).toBe("Első");
    expect(props.onReviewState).toHaveBeenLastCalledWith(expect.objectContaining({ canReview: false }));
    fireEvent.click(screen.getByRole("button", { name: "v2" }));
    expect((screen.getByLabelText("Poszt szövege") as HTMLTextAreaElement).value).toBe("Helyi szerkesztés");
    view.rerender(<DraftEditor {...props} detail={item("idea-1", ["Első", "Második", "ChatGPT változat"])} />);
    expect((screen.getByLabelText("Poszt szövege") as HTMLTextAreaElement).value).toBe("Helyi szerkesztés");
    expect(screen.getByText(/Új mentett verzió érkezett/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Új verzió mentése" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("loads a received first draft when there is no local work", () => {
    const props = editorProps(item());
    const view = render(<DraftEditor {...props} />);
    view.rerender(<DraftEditor {...props} detail={item("idea-1", ["Elkészült a draft"])} />);
    expect((screen.getByLabelText("Poszt szövege") as HTMLTextAreaElement).value).toBe("Elkészült a draft");
    expect(props.onReviewState).toHaveBeenLastCalledWith(expect.objectContaining({ canReview: true }));
  });

  it("keeps a working copy when switching documents and does not leak it to another owner", () => {
    const props = editorProps();
    const view = render(<DraftEditor {...props} />);
    fireEvent.change(screen.getByLabelText("Poszt szövege"), { target: { value: "Megőrzött szöveg" } });
    view.rerender(<DraftEditor {...props} detail={item("idea-2")} />);
    view.rerender(<DraftEditor {...props} />);
    expect((screen.getByLabelText("Poszt szövege") as HTMLTextAreaElement).value).toBe("Megőrzött szöveg");
    view.unmount();
    render(<DraftEditor {...props} account="other-owner" />);
    expect((screen.getByLabelText("Poszt szövege") as HTMLTextAreaElement).value).toBe("Eredeti szöveg");
  });

  it("disables approval while the editor is dirty or showing history", () => {
    const noop = vi.fn();
    const props = { detail: item("idea-1", ["Szöveg"]), profile: null, busy: false, reviewBlocked: true,
      onRequestChanges: noop, onApprove: noop, onRevokeApproval: noop, onPlan: noop,
      onConfirmExternal: noop, onMarkPublished: noop, onPublishNow: noop, onRecordPerformance: noop, onSaveProfile: noop };
    const view = render(<WorkflowInspector {...props} />);
    expect((screen.getByRole("button", { name: "v1 jóváhagyása" }) as HTMLButtonElement).disabled).toBe(true);
    view.rerender(<WorkflowInspector {...props} reviewBlocked={false} />);
    fireEvent.click(screen.getByRole("button", { name: "v1 jóváhagyása" }));
    expect(noop).toHaveBeenCalledTimes(1);
  });
});

describe("Publication", () => {
  function inspectorProps(overrides: Partial<ReturnType<typeof item>> = {}) {
    const noop = vi.fn();
    const detail = { ...item("idea-1", ["Kész szöveg"]), ...overrides };
    return { detail, profile: null, busy: false, reviewBlocked: false,
      onRequestChanges: noop, onApprove: noop, onRevokeApproval: noop, onPlan: noop,
      onConfirmExternal: noop, onMarkPublished: noop, onPublishNow: vi.fn().mockResolvedValue(detail),
      onRecordPerformance: noop, onSaveProfile: noop };
  }
  const approval = { id: "approval-1", contentItemId: "idea-1", versionId: "idea-1-v1",
    contentHash: "1".repeat(64), approvedAt: "2026-09-08T11:00:00Z" };

  it("records a post published without a plan only after approval", async () => {
    const unapproved = inspectorProps();
    const view = render(<WorkflowInspector {...unapproved} />);
    fireEvent.click(screen.getByRole("button", { name: "Megjelenés" }));
    expect((screen.getByRole("button", { name: "Most tettem közzé" }) as HTMLButtonElement).disabled).toBe(true);

    const props = inspectorProps({ activeApproval: approval, status: "approved" });
    view.rerender(<WorkflowInspector {...props} />);
    const link = "https://www.linkedin.com/posts/example-activity-1";
    fireEvent.change(screen.getAllByLabelText("A poszt linkje (nem kötelező)")[0], { target: { value: link } });
    fireEvent.click(screen.getByRole("button", { name: "Most tettem közzé" }));
    await waitFor(() => expect(props.onPublishNow).toHaveBeenCalledWith(link, ""));
  });

  it("shows when and where a post was published", () => {
    const props = inspectorProps({ activeApproval: approval, publicationPlan: {
      id: "plan-1", contentItemId: "idea-1", versionId: "idea-1-v1", plannedFor: "2026-09-08T12:00:00Z",
      timezone: "Europe/Budapest", status: "published", externalConfirmationNote: null,
      publishedAt: "2026-09-08T12:00:00Z", postUrl: "https://www.linkedin.com/posts/example-activity-1",
      createdAt: "2026-09-08T12:00:00Z", updatedAt: "2026-09-08T12:00:00Z" } });
    render(<WorkflowInspector {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Megjelenés" }));
    expect(screen.getByRole("link", { name: "Poszt megnyitása" }).getAttribute("href"))
      .toBe("https://www.linkedin.com/posts/example-activity-1");
    expect(screen.queryByRole("button", { name: "Most tettem közzé" })).toBeNull();
  });
});

describe("Quick capture", () => {
  it.each([["Mentés későbbre", false], ["Mentés és draftkérés", true]])("keeps %s as an explicit intent", async (button, requested) => {
    const onSaved = vi.fn();
    const capture = vi.fn().mockResolvedValue(item());
    render(<CaptureDialog account="test-owner" busy={false} onClose={vi.fn()} onSaved={onSaved}
      onCaptureIdea={capture} onCaptureResearch={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Az ötleted"), { target: { value: "Séta közbeni gondolat" } });
    fireEvent.click(screen.getByRole("button", { name: button as string }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ id: "idea-1" }), requested));
    expect(capture).toHaveBeenCalledWith("Séta közbeni gondolat", "", expect.any(String));
    expect(localStorage.getItem(workspaceKey("test-owner", "capture"))).toBeNull();
  });

  it("restores an interrupted capture", () => {
    const props = { account: "test-owner", busy: false, onClose: vi.fn(), onSaved: vi.fn(), onCaptureIdea: vi.fn(), onCaptureResearch: vi.fn() };
    const view = render(<CaptureDialog {...props} />);
    fireEvent.change(screen.getByLabelText("Az ötleted"), { target: { value: "Még nem küldtem el" } });
    view.unmount();
    render(<CaptureDialog {...props} />);
    expect((screen.getByLabelText("Az ötleted") as HTMLTextAreaElement).value).toBe("Még nem küldtem el");
  });
});
