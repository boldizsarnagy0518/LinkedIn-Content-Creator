"use client";

import { BookOpen, Lightbulb, X } from "lucide-react";
import { useRef, useState } from "react";
import { Modal } from "@/app/_components/modal";
import { isCaptureNote, readLocal, writeLocal, workspaceKey, type CaptureNote } from "@/lib/workspace-drafts";
import type { ContentItemDetail } from "@/types/content";
import styles from "@/app/workspace.module.css";

type Props = {
  account: string;
  busy: boolean;
  error?: string | null;
  onClose: () => void;
  onSaved: (item: ContentItemDetail, draftRequested: boolean) => void;
  onCaptureIdea: (idea: string, title?: string, requestKey?: string) => Promise<ContentItemDetail | null>;
  onCaptureResearch: (topic: string, notes: string, urls: string[], requestKey?: string) => Promise<ContentItemDetail | null>;
};

export function CaptureDialog({ account, busy, error, onClose, onSaved, onCaptureIdea, onCaptureResearch }: Props) {
  const storageKey = workspaceKey(account, "capture");
  const [note, setNote] = useState<CaptureNote>(() => readLocal(storageKey, isCaptureNote) ?? {
    mode: "idea", title: "", body: "", urls: ""
  });
  const [stored, setStored] = useState(true);
  const submitting = useRef(false);
  function update(patch: Partial<CaptureNote>) {
    const next = { ...note, ...patch, requestKey: crypto.randomUUID() };
    setNote(next);
    setStored(writeLocal(storageKey, next));
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || busy) return;
    submitting.current = true;
    const draftRequested = (event.nativeEvent as SubmitEvent).submitter?.getAttribute("value") === "draft";
    const requestKey = note.requestKey ?? crypto.randomUUID();
    setNote({ ...note, requestKey });
    setStored(writeLocal(storageKey, { ...note, requestKey }));
    try {
      const result = note.mode === "idea"
        ? await onCaptureIdea(note.body, note.title, requestKey)
        : await onCaptureResearch(note.title, note.body, note.urls.split(/\r?\n/).map((url) => url.trim()).filter(Boolean), requestKey);
      if (result) { writeLocal(storageKey, null); onSaved(result, draftRequested); }
    } finally { submitting.current = false; }
  }
  const valid = note.body.trim().length >= 3 && (note.mode === "idea" || (note.title.trim().length >= 3 && note.urls.trim().length > 0));
  return <Modal titleId="capture-title" onClose={() => { if (!busy) onClose(); }}>
    <header className={styles.dialogHeader}>
      <div><p className={styles.eyebrow}>Egy gondolatból indul</p><h2 id="capture-title">Mi jutott eszedbe?</h2></div>
      <button className={styles.iconButton} onClick={onClose} disabled={busy} aria-label="Bezárás"><X size={18} /></button>
    </header>
    <div className={styles.segmentedControl}>
      <button type="button" disabled={busy} data-active={note.mode === "idea"} aria-pressed={note.mode === "idea"} onClick={() => update({ mode: "idea" })}><Lightbulb size={16} /> Saját ötlet</button>
      <button type="button" disabled={busy} data-active={note.mode === "research"} aria-pressed={note.mode === "research"} onClick={() => update({ mode: "research" })}><BookOpen size={16} /> Kutatás</button>
    </div>
    <form className={styles.captureForm} onSubmit={submit}>
      {error && <p className={styles.inlineNote} role="alert">{error}</p>}
      <label><span>{note.mode === "idea" ? "Az ötleted" : "Kutatási jegyzet"}</span>
        <textarea value={note.body} onChange={(event) => update({ body: event.target.value })}
          placeholder="Írd le, ahogy eszedbe jutott. Diktálhatsz is a telefon billentyűzetével."
          rows={7} maxLength={note.mode === "idea" ? 6000 : 50000} required autoFocus disabled={busy} />
      </label>
      {note.mode === "research" ? <>
        <label><span>Téma</span><input value={note.title} onChange={(event) => update({ title: event.target.value })} maxLength={160} required disabled={busy} /></label>
        <label><span>Forráslinkek, soronként egy</span><textarea value={note.urls} onChange={(event) => update({ urls: event.target.value })} rows={3} required disabled={busy} /></label>
      </> : <details><summary>Cím hozzáadása (opcionális)</summary>
        <label><span className={styles.srOnly}>Cím</span><input value={note.title} onChange={(event) => update({ title: event.target.value })} placeholder="Ha üres, az ötletből készül cím" maxLength={160} disabled={busy} /></label>
      </details>}
      {note.body && <p className={styles.storageNote} role="status">{stored
        ? "Munkapéldány ezen az eszközön. A mentés után lesz elérhető a többi eszközödön."
        : "Az eszköz nem tudja megőrizni a munkapéldányt. Bezárás előtt mentsd vagy másold ki."}</p>}
      <footer className={styles.captureActions}>
        <button type="submit" value="later" className={styles.secondaryButton} disabled={!valid || busy}>Mentés későbbre</button>
        <button type="submit" value="draft" className={styles.primaryButton} disabled={!valid || busy}>Mentés és draftkérés</button>
      </footer>
      <p className={styles.handoffNote}>A draftkérés a ChatGPT-be másolható. A szöveg a csatlakoztatott beszélgetésben készül el.</p>
    </form>
  </Modal>;
}
