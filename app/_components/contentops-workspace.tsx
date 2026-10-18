"use client";

import { Download, LogOut, Plus, RefreshCw, UserRound, Wifi, WifiOff } from "lucide-react";
import { AuthorMemoryDialog } from "@/app/_components/author-memory";
import { useCallback, useState } from "react";
import { CaptureDialog } from "@/app/_components/capture-dialog";
import { ContentQueue } from "@/app/_components/content-queue";
import { DraftEditor, type ReviewState } from "@/app/_components/draft-editor";
import { HostHandoff } from "@/app/_components/host-handoff";
import { WorkflowInspector } from "@/app/_components/workflow-inspector";
import { useContentOpsWorkspace } from "@/app/_hooks/use-contentops-workspace";
import * as api from "@/lib/contentops-api";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { ContentItemDetail } from "@/types/content";
import styles from "@/app/workspace.module.css";

type Props = { accountLabel?: string; authEnabled?: boolean };

export function ContentOpsWorkspace({ accountLabel = "Local workspace", authEnabled = false }: Props) {
  const workspace = useContentOpsWorkspace();
  const [captureOpen, setCaptureOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [handoff, setHandoff] = useState<{ itemId: string; title: string; revision: boolean } | null>(null);
  const [mobileView, setMobileView] = useState<"list" | "document">("list");
  const [review, setReview] = useState<ReviewState | null>(null);
  const onReviewState = useCallback((state: ReviewState) => setReview((previous) =>
    JSON.stringify(previous) === JSON.stringify(state) ? previous : state), []);
  const current = workspace.detail?.versions.at(-1) ?? null;
  const plan = workspace.detail?.publicationPlan ?? null;
  const busy = Boolean(workspace.busy) || workspace.loading;
  const reviewBlocked = !review || review.itemId !== workspace.detail?.id ||
    review.currentVersionId !== workspace.detail?.currentVersionId || !review.canReview;

  async function downloadExport() {
    try {
      const response = await fetch("/api/workflow/content-items/export", { cache: "no-store" });
      if (!response.ok) throw new Error("Export failed");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `contentops-export-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click(); URL.revokeObjectURL(url);
    } catch { workspace.showNotice("Az export nem sikerült. Próbáld újra."); }
  }
  const withDetail = (action: (id: string) => Promise<ContentItemDetail | null>) =>
    workspace.detail ? action(workspace.detail.id) : Promise.resolve(null);
  const openHandoff = (item: ContentItemDetail, revision = false) => setHandoff({ itemId: item.id, title: item.title, revision });

  return <div className={styles.workspace} data-mobile-view={mobileView}>
    <header className={styles.appHeader}>
      <a className={styles.brand} href="#desk" aria-label="ContentOps kezdőlap" onClick={() => setMobileView("list")}><span className={styles.brandMark}>CO</span><span>ContentOps</span></a>
      <span className={styles.headerRule} aria-hidden="true" />
      <div className={styles.connectionState} title={workspace.connected ? "A munkatér elérhető. Az új verziókat automatikusan ellenőrizzük." : "A munkatér kapcsolata még nem igazolt."}>
        {workspace.connected ? <Wifi size={14} /> : <WifiOff size={14} />}<span>{accountLabel}</span>
      </div>
      <div className={styles.headerActions}>
        <button className={styles.primaryButton} onClick={() => setCaptureOpen(true)}><Plus size={16} /> Új ötlet</button>
        <button className={styles.iconButton} onClick={() => setMemoryOpen(true)} title="Profil és korábbi posztok" aria-label="Profil és korábbi posztok"><UserRound size={17} /></button>
        <button className={styles.iconButton} onClick={() => void downloadExport()} title="Exportálás" aria-label="Exportálás"><Download size={17} /></button>
        <button className={styles.iconButton} disabled={busy} onClick={() => void workspace.refresh()} title="Frissítés" aria-label="Frissítés"><RefreshCw size={17} className={workspace.loading ? styles.spinning : undefined} /></button>
        {authEnabled && <button className={styles.iconButton} onClick={async () => {
          await createSupabaseBrowserClient().auth.signOut(); window.location.assign("/login");
        }} title="Kijelentkezés" aria-label="Kijelentkezés"><LogOut size={17} /></button>}
      </div>
    </header>
    <div className={styles.workspaceGrid} id="desk">
      <ContentQueue items={workspace.items} selectedId={workspace.detail?.id ?? null} filter={workspace.filter} loading={workspace.loading}
        onFilterChange={workspace.setFilter} onSelect={(id) => { setMobileView("document"); void workspace.selectItem(id); }} onCapture={() => setCaptureOpen(true)} />
      <DraftEditor account={accountLabel} detail={workspace.detail} busy={busy} onReviewState={onReviewState}
        onBack={() => setMobileView("list")} onCapture={() => setCaptureOpen(true)}
        onHandoff={() => { if (workspace.detail) openHandoff(workspace.detail, Boolean(current)); }}
        onSaveVersion={(body, summary, expected) => withDetail((id) => workspace.mutate("Szöveg elmentve", () => api.saveDraftVersion(id, body, summary, expected)))}
        onArchive={() => withDetail((id) => workspace.mutate("Ötlet archiválva", () => api.archiveContentItem(id)))} />
      <WorkflowInspector detail={workspace.detail} profile={workspace.profile} busy={busy} reviewBlocked={reviewBlocked}
        onRequestChanges={async (feedback) => {
          if (!current || reviewBlocked) return null;
          const result = await withDetail((id) => workspace.mutate("Visszajelzés elmentve", () => api.requestChanges(id, current.id, feedback)));
          if (result) openHandoff(result, true);
          return result;
        }}
        onApprove={() => current && !reviewBlocked ? withDetail((id) => workspace.mutate("Szöveg jóváhagyva", () => api.approveDraft(id, current.id, current.contentHash))) : Promise.resolve(null)}
        onRevokeApproval={() => withDetail((id) => workspace.mutate("Jóváhagyás visszavonva", () => api.revokeApproval(id)))}
        onPlan={(plannedFor, timezone) => current && !reviewBlocked ? withDetail((id) => workspace.mutate("Megjelenés tervezve", () => api.setPublicationPlan(id, current.id, plannedFor, timezone))) : Promise.resolve(null)}
        onConfirmExternal={(note) => plan ? withDetail((id) => workspace.mutate("Időzítés visszaigazolva", () => api.confirmExternalSchedule(id, plan.id, note))) : Promise.resolve(null)}
        onMarkPublished={(note) => plan ? withDetail((id) => workspace.mutate("Publikálás visszaigazolva", () => api.markPublished(id, plan.id, note))) : Promise.resolve(null)}
        onRecordPerformance={(metrics) => withDetail((id) => workspace.mutate("Eredmények elmentve", () => api.recordPerformance(id, metrics)))} onSaveProfile={workspace.saveProfile} />
    </div>
    {workspace.error && <div className={styles.errorToast} role="alert">{workspace.error}</div>}
    {workspace.notice && !workspace.error && <div className={styles.noticeToast} role="status">{workspace.notice}</div>}
    {captureOpen && <CaptureDialog account={accountLabel} busy={Boolean(workspace.busy)} error={workspace.error} onClose={() => setCaptureOpen(false)}
      onCaptureIdea={workspace.captureIdea} onCaptureResearch={workspace.captureResearch}
      onSaved={(item, requested) => { setCaptureOpen(false); setMobileView("document"); if (requested) openHandoff(item); }} />}
    {handoff && <HostHandoff {...handoff} onClose={() => setHandoff(null)} />}
    {memoryOpen && <AuthorMemoryDialog onClose={() => setMemoryOpen(false)} />}
  </div>;
}
