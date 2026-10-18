"use client";

import { useEffect, useRef, useState } from "react";
import { Modal } from "@/app/_components/modal";
import { getAuthorMemory, saveAuthorMemory } from "@/lib/contentops-api";
import type { AuthorMemory } from "@/types/content";
import styles from "@/app/workspace.module.css";

export function AuthorMemoryDialog({ onClose }: { onClose: () => void }) {
  const [memory, setMemory] = useState<AuthorMemory | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const submitting = useRef(false);
  useEffect(() => {
    let active = true;
    getAuthorMemory().then((value) => { if (active) setMemory(value); })
      .catch(() => { if (active) setError("A profil betöltése nem sikerült. Zárd be és nyisd meg újra."); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    function warn(event: BeforeUnloadEvent) { if (dirty) event.preventDefault(); }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function close() {
    if (!busy && (!dirty || window.confirm("A nem mentett profilmódosítások elvesznek. Bezárod?"))) onClose();
  }
  function update(value: AuthorMemory) { setMemory(value); setDirty(true); setSaved(false); }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!memory || submitting.current) return;
    submitting.current = true; setBusy(true); setError(null);
    try { setMemory(await saveAuthorMemory(memory)); setDirty(false); setSaved(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "A mentés nem sikerült."); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <Modal titleId="author-memory-title" onClose={close}>
    <header className={styles.dialogHeader}>
      <div><p className={styles.eyebrow}>A saját hangod alapjai</p><h2 id="author-memory-title">Profil és korábbi posztok</h2></div>
      <button className={styles.iconButton} onClick={close} disabled={busy} aria-label="Bezárás">×</button>
    </header>
    <form className={styles.captureForm} onSubmit={save}>
      {error && <p role="alert">{error}</p>}
      {!memory ? <p>Profil betöltése…</p> : <>
        <label><span>Szakmai háttér és témák</span>
          <textarea rows={6} maxLength={12000} value={memory.background} disabled={busy}
            placeholder="Mivel foglalkozol, milyen tapasztalataid vannak, miről szeretsz írni? Milyen célból posztolsz?"
            onChange={(event) => update({ ...memory, background: event.target.value })} />
        </label>
        <p className={styles.handoffNote}>Másold be a saját korábbi posztjaidat. A ChatGPT ezekből kap mintát a témáidra, szóhasználatodra és a szövegeid felépítésére. Nem indul külön modellbetanítás.</p>
        {memory.past_posts.map((post, index) => <fieldset key={index} className={styles.memoryPost} disabled={busy}>
          <legend>Korábbi poszt {index + 1}</legend>
          <label><span>Cím</span><input value={post.title} maxLength={160} required onChange={(event) => update({ ...memory, past_posts: memory.past_posts.map((entry, i) => i === index ? { ...entry, title: event.target.value } : entry) })} /></label>
          <label><span>Témák</span><input value={post.topics} maxLength={500} placeholder="Például: Python, tanulás, saját projektek" onChange={(event) => update({ ...memory, past_posts: memory.past_posts.map((entry, i) => i === index ? { ...entry, topics: event.target.value } : entry) })} /></label>
          <label><span>Poszt szövege</span><textarea rows={7} value={post.body} maxLength={5000} required onChange={(event) => update({ ...memory, past_posts: memory.past_posts.map((entry, i) => i === index ? { ...entry, body: event.target.value } : entry) })} /></label>
          <label className={styles.memoryToggle}><input type="checkbox" checked={post.use_as_example} onChange={(event) => update({ ...memory, past_posts: memory.past_posts.map((entry, i) => i === index ? { ...entry, use_as_example: event.target.checked } : entry) })} /><span>Használja írásmintaként</span></label>
          <button type="button" className={styles.secondaryButton} onClick={() => { if (window.confirm("Eltávolítod ezt a posztot a gyűjteményből?")) update({ ...memory, past_posts: memory.past_posts.filter((_, i) => i !== index) }); }}>Poszt eltávolítása</button>
        </fieldset>)}
        <button type="button" className={styles.secondaryButton} disabled={busy || memory.past_posts.length >= 50} onClick={() => update({ ...memory, past_posts: [{ title: "", body: "", topics: "", use_as_example: true }, ...memory.past_posts] })}>Korábbi poszt hozzáadása ({memory.past_posts.length}/50)</button>
        <p className={styles.handoffNote}>Írás előtt az MCP átadja a hátteredet, az első kiválasztott mintákat és az alkalmazásban jóváhagyott szövegeidet. A hangprofilban megadott kifejezett kéréseid elsőbbséget élveznek.</p>
        <button className={styles.primaryButton} disabled={busy || !dirty || memory.past_posts.some((post) => !post.title.trim() || !post.body.trim())}>{busy ? "Mentés…" : "Profil és posztok mentése"}</button>
        {saved && <p role="status">Elmentve. A következő MCP-s draftkérés már használhatja.</p>}
      </>}
    </form>
  </Modal>;
}
