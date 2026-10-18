"use client";

import { Check, Clipboard, ExternalLink, X } from "lucide-react";
import { useState } from "react";
import { Modal } from "@/app/_components/modal";
import { buildDraftPrompt } from "@/lib/workspace-drafts";
import styles from "@/app/workspace.module.css";

export function HostHandoff({ itemId, title, revision, onClose }: {
  itemId: string; title: string; revision?: boolean; onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);
  const prompt = buildDraftPrompt(itemId, revision);
  return <Modal titleId="handoff-title" onClose={onClose}>
    <header className={styles.dialogHeader}>
      <div><p className={styles.eyebrow}>Az ötleted elmentve</p><h2 id="handoff-title">Folytasd a ChatGPT-ben</h2></div>
      <button className={styles.iconButton} aria-label="Bezárás" onClick={onClose}><X size={18} /></button>
    </header>
    <div className={styles.captureForm}>
      <strong>{title}</strong>
      <p className={styles.handoffNote}>Másold a kérést egy olyan beszélgetésbe, amelyben a ContentOps csatlakoztatva van. Küldd el ott; a szöveg elkészítése a beszélgetésben indul.</p>
      <textarea className={styles.promptText} aria-label="ChatGPT-nek átadható kérés" value={prompt} readOnly rows={8}
        onFocus={(event) => event.currentTarget.select()} />
      {error && <p role="alert">A másolás nem sikerült. Jelöld ki és másold a fenti szöveget.</p>}
      <div className={styles.actionRow}>
        <button className={styles.primaryButton} onClick={async () => {
          try { await navigator.clipboard.writeText(prompt); setCopied(true); setError(false); }
          catch { setError(true); }
        }}>{copied ? <Check size={16} /> : <Clipboard size={16} />}{copied ? "Kérés másolva" : "Kérés másolása"}</button>
        <a className={styles.secondaryButton} href="https://chatgpt.com/" target="_blank" rel="noreferrer">
          ChatGPT megnyitása <ExternalLink size={14} />
        </a>
      </div>
      <p className={styles.handoffNote}>Ha a ChatGPT elmentette a draftot, itt automatikusan megjelenik. A kapcsolat meglétét innen nem tudjuk ellenőrizni.</p>
      <button className={styles.secondaryButton} onClick={onClose}>Vissza az ötlethez</button>
    </div>
  </Modal>;
}
