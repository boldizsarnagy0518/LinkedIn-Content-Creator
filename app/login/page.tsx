"use client";

import { ArrowRight, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { getSupabasePublicConfig } from "@/lib/supabase/config";
import { safeReturnPath } from "@/lib/auth-return";
import styles from "@/app/login/login.module.css";

export default function LoginPage() {
  const configured = Boolean(getSupabasePublicConfig());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signIn(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const { error: authError } = await createSupabaseBrowserClient().auth.signInWithPassword({ email, password });
    if (authError) {
      setError(authError.message);
      setBusy(false);
      return;
    }
    window.location.assign(safeReturnPath(new URLSearchParams(window.location.search).get("next")));
  }

  return (
    <main className={styles.login}>
      <header className={styles.masthead}>
        <span className={styles.brandMark}>CO</span>
        <strong>ContentOps</strong>
        <span>Private editorial desk</span>
      </header>
      <section className={styles.sheet}>
        <div className={styles.folio}>01 / ACCESS</div>
        <div className={styles.intro}>
          <p>Every publishable sentence has a source, a version, and a human decision behind it.</p>
          <span>Capture. Draft. Review. Publish.</span>
        </div>
        <form className={styles.form} onSubmit={signIn}>
          <div className={styles.formHeading}>
            <LockKeyhole size={20} />
            <div><span>Owner access</span><h1>Open the desk</h1></div>
          </div>
          {!configured && <p className={styles.configNote}>Supabase Auth is not configured. Local development opens directly at the root route.</p>}
          <label><span>Email</span><input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required disabled={!configured} /></label>
          <label><span>Password</span><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={!configured} /></label>
          {error && <p className={styles.error} role="alert">{error}</p>}
          <button disabled={!configured || busy}>{busy ? "Opening..." : "Enter workspace"}<ArrowRight size={17} /></button>
        </form>
      </section>
      <footer className={styles.footer}>Human-controlled publishing / exact-version approval</footer>
    </main>
  );
}
