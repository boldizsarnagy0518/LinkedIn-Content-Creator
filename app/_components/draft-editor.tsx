"use client";

import { Archive, ArrowLeft, Check, Clipboard, ExternalLink, FileClock, MessageSquareText, Save } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { StatusMarker } from "@/app/_components/status-marker";
import { isWorkingCopy, readLocal, writeLocal, workspaceKey, type WorkingCopy } from "@/lib/workspace-drafts";
import type { ContentItemDetail } from "@/types/content";
import styles from "@/app/workspace.module.css";

export type ReviewState = { itemId: string; currentVersionId: string | null; canReview: boolean; dirty: boolean };
type Props = {
  account: string;
  detail: ContentItemDetail | null;
  busy: boolean;
  onSaveVersion: (body: string, summary: string, expectedVersionId: string) => Promise<ContentItemDetail | null>;
  onArchive: () => Promise<unknown>;
  onReviewState: (state: ReviewState) => void;
  onHandoff: () => void;
  onBack: () => void;
  onCapture: () => void;
};

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("hu", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export function DraftEditor(props: Props) {
  if (!props.detail) return <main className={styles.editorEmpty}>
    <div className={styles.proofMark} aria-hidden="true">¶</div>
    <p className={styles.eyebrow}>A következő posztod itt kezdődik</p>
    <h2>Őrizd meg, ami eszedbe jutott.</h2>
    <p>Ments egy ötletet későbbre, vagy készíts elő egy draftkérést.</p>
    <button className={styles.primaryButton} onClick={props.onCapture}>Új ötlet</button>
  </main>;
  // Remount on server versions, restoring an unsaved working copy if one exists.
  return <DraftDocument key={`${props.detail.id}:${props.detail.currentVersionId ?? "source"}`} {...props} detail={props.detail} />;
}

function DraftDocument(props: Props & { detail: ContentItemDetail }) {
  const { detail, busy, onReviewState } = props;
  const current = detail.versions.at(-1) ?? null;
  const currentId = current?.id ?? "source";
  const storageKey = workspaceKey(props.account, `draft:${detail.id}`);
  const [copy, setCopy] = useState<WorkingCopy>(() => {
    const recovered = readLocal(storageKey, isWorkingCopy);
    if (recovered && recovered.body.trim() !== (current?.body ?? "")) return recovered;
    return { baseVersionId: currentId, body: current?.body ?? "", summary: "" };
  });
  const [selectedVersionId, setSelectedVersionId] = useState(currentId);
  const [stored, setStored] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const mounted = useRef(true);
  const isHistory = selectedVersionId !== currentId;
  const selected = detail.versions.find((version) => version.id === selectedVersionId) ?? current;
  const base = detail.versions.find((version) => version.id === copy.baseVersionId);
  const dirty = copy.body !== (base?.body ?? "") || copy.summary !== "";
  const conflict = copy.baseVersionId !== currentId;
  const visibleBody = isHistory ? selected?.body ?? "" : copy.body;
  const canReview = Boolean(current && !isHistory && !dirty && !conflict);
  const canSave = !isHistory && !conflict && copy.body.trim().length > 0 && copy.body.trim() !== (current?.body ?? "");
  const archived = detail.status === "archived";

  useEffect(() => {
    onReviewState({ itemId: detail.id, currentVersionId: detail.currentVersionId, canReview, dirty });
  }, [onReviewState, detail.id, detail.currentVersionId, canReview, dirty]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!dirty || stored) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, stored]);

  function update(next: WorkingCopy) {
    setCopy(next);
    const original = detail.versions.find((version) => version.id === next.baseVersionId)?.body ?? "";
    setStored(writeLocal(storageKey, next.body === original && !next.summary ? null : next));
  }
  function resetToCurrent() {
    if (dirty && !window.confirm("Eldobod a helyi módosításokat és megnyitod a legfrissebb mentett verziót?")) return;
    update({ baseVersionId: currentId, body: current?.body ?? "", summary: "" });
    setSelectedVersionId(currentId);
  }
  async function copyVisible() {
    try { await navigator.clipboard.writeText(visibleBody || detail.rawInput); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  async function save() {
    if (!canSave || busy || archived) return;
    const result = await props.onSaveVersion(copy.body, copy.summary, copy.baseVersionId);
    if (!result) return;
    writeLocal(storageKey, null);
    if (mounted.current) setCopy({ baseVersionId: result.currentVersionId ?? "source", body: result.versions.at(-1)?.body ?? "", summary: "" });
  }

  return <main className={styles.editor}>
    <button className={styles.mobileBack} onClick={props.onBack}><ArrowLeft size={16} /> Ötletek és szövegek</button>
    <header className={styles.documentHeader}>
      <div className={styles.documentMeta}><StatusMarker status={detail.status} /><span>{detail.sourceKind === "research" ? "Kutatás" : "Saját ötlet"}</span><time dateTime={detail.updatedAt}>{formatTimestamp(detail.updatedAt)}</time></div>
      <div className={styles.documentTitleRow}>
        <h1>{detail.title}</h1>
        <button className={styles.iconButton} onClick={() => void copyVisible()} title="Látható szöveg másolása" aria-label="Látható szöveg másolása">{copied ? <Check size={18} /> : <Clipboard size={18} />}</button>
        {!archived && <button className={styles.iconButton} disabled={busy} onClick={() => {
          if (window.confirm("Archiválod ezt az ötletet? A mentett előzmények megmaradnak.")) void props.onArchive();
        }} title="Archiválás" aria-label="Archiválás"><Archive size={18} /></button>}
      </div>
      {copyError && <p role="alert">A másolás nem sikerült. Jelöld ki és másold a szöveget.</p>}
    </header>
    <details className={styles.sourceDetails} open={!current}>
      <summary>Eredeti ötlet és források</summary>
      <section className={styles.sourceBand}><p className={styles.marginLabel}>ÖTLET</p><div><p>{detail.rawInput}</p>
        <ul className={styles.sourceList}>{detail.sources.map((source) => <li key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title ?? new URL(source.url).hostname}<ExternalLink size={12} /></a></li>)}</ul>
      </div></section>
    </details>
    {!archived && <div className={`${styles.draftHandoff} ${current ? styles.draftHandoffCompact : ""}`}>
      <div><strong>{current ? "Finomítanád a szöveget?" : "Az ötletből lehet poszt."}</strong><p>{current ? "Szerkeszd itt, vagy add át a visszajelzésedet a ChatGPT-nek." : "Írd meg itt, vagy kérj teljes draftot a csatlakoztatott ChatGPT-beszélgetésben."}</p></div>
      <button className={styles.secondaryButton} onClick={props.onHandoff} disabled={busy || dirty || conflict || isHistory}><MessageSquareText size={16} /> {current ? "Folytatás ChatGPT-ben" : "Draftkérés ChatGPT-ben"}</button>
    </div>}
    {conflict && <div className={styles.conflictBanner} role="status">
      <strong>Új mentett verzió érkezett. A helyi szövegedet megőriztük.</strong>
      <p>Hasonlítsd össze a kettőt. A saját változatodat csak a legfrissebb szöveg átnézése után mentsd.</p>
      <div className={styles.actionRow}>
        <button className={styles.secondaryButton} onClick={() => setShowComparison((value) => !value)}>Összehasonlítás</button>
        <button className={styles.secondaryButton} onClick={resetToCurrent}>Mentett verzió megnyitása</button>
        <button className={styles.secondaryButton} onClick={() => {
          if (window.confirm("Átnézted a legfrissebb verziót? A helyi szöveged új változatként lesz menthető; minden korábbi verzió megmarad.")) update({ ...copy, baseVersionId: currentId });
        }}>Helyi szöveg megtartása</button>
      </div>
    </div>}
    {detail.versions.length > 0 && <nav className={styles.versionRail} aria-label="Szövegverziók"><FileClock size={15} />
      {detail.versions.map((version) => <button key={version.id} type="button" data-active={selectedVersionId === version.id} aria-pressed={selectedVersionId === version.id} onClick={() => setSelectedVersionId(version.id)} title={version.changeSummary ?? undefined}>v{version.versionNumber}</button>)}
      <button className={styles.compareButton} onClick={() => setShowComparison((value) => !value)} aria-pressed={showComparison}>Összehasonlítás</button>
    </nav>}
    {showComparison && <section className={styles.comparison} aria-label="Verzió-összehasonlítás">
      <article><h3>{conflict ? "Legfrissebb mentett szöveg" : "Előző mentett szöveg"}</h3><p>{conflict ? current?.body : detail.versions.at(-2)?.body ?? "Még nincs korábbi verzió."}</p></article>
      <article><h3>{isHistory ? "Kiválasztott verzió" : "Munkapéldány"}</h3><p>{visibleBody}</p></article>
    </section>}
    <section className={styles.manuscript}><p className={styles.marginLabel}>{isHistory ? "ELŐZMÉNY" : "SZÖVEG"}</p>
      <textarea aria-label="Poszt szövege" value={visibleBody} placeholder="Ide írhatod vagy beillesztheted az első draftot is."
        onChange={(event) => { update({ ...copy, body: event.target.value }); setCopied(false); }}
        readOnly={isHistory || archived || busy} maxLength={50000} spellCheck />
    </section>
    {!isHistory && !archived && <footer className={styles.editorFooter}>
      <label><span className={styles.srOnly}>Változás rövid leírása</span><input value={copy.summary} onChange={(event) => update({ ...copy, summary: event.target.value })} placeholder="Mi változott? (opcionális)" maxLength={2000} disabled={busy} /></label>
      <span className={styles.characterCount}>{copy.body.length.toLocaleString("hu")} karakter</span>
      <button className={styles.primaryButton} disabled={!canSave || busy} onClick={() => void save()}><Save size={16} />{current ? "Új verzió mentése" : "Első draft mentése"}</button>
      <p className={styles.saveState} role="status">{dirty ? (stored ? "Módosítások ezen az eszközön · még nem mentett verzió" : "A helyi mentés nem elérhető · ments vagy másolj bezárás előtt") : "Minden módosítás mentve"}</p>
    </footer>}
  </main>;
}
