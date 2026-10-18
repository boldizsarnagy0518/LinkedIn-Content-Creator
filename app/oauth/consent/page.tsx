import { redirect } from "next/navigation";
import type { Route } from "next";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import styles from "@/app/login/login.module.css";

export const dynamic = "force-dynamic";
export const metadata = { title: "Hozzáférés engedélyezése", robots: { index: false, follow: false } };

function validId(value: unknown): value is string {
  return typeof value === "string" && /^[a-zA-Z0-9_-]{1,128}$/.test(value);
}

function hostRedirect(value: string): never {
  const url = new URL(value);
  if (url.protocol !== "https:") throw new Error("A visszatérési címnek HTTPS-címnek kell lennie.");
  // This URL comes from Supabase's validated authorization response, never from query input.
  redirect(url.toString() as Route);
}

async function ownerClient(authorizationId: string) {
  const client = await createSupabaseServerClient();
  if (!client || !process.env.CONTENTOPS_OWNER_USER_ID || !process.env.MCP_OAUTH_CLIENT_ID) {
    throw new Error("A hozzáférés engedélyezése még nincs beállítva a szerveren.");
  }
  const { data, error } = await client.auth.getUser();
  if (error || !data.user) redirect(`/login?next=${encodeURIComponent(`/oauth/consent?authorization_id=${authorizationId}`)}`);
  if (data.user.id !== process.env.CONTENTOPS_OWNER_USER_ID) throw new Error("Csak a műhely tulajdonosa adhat hozzáférést.");
  return client;
}

async function decide(form: FormData) {
  "use server";
  const id = form.get("authorization_id");
  const decision = form.get("decision");
  if (!validId(id) || (decision !== "approve" && decision !== "deny")) throw new Error("Érvénytelen kérés.");
  const client = await ownerClient(id);
  const { data: details, error: detailsError } = await client.auth.oauth.getAuthorizationDetails(id);
  if (detailsError || !details) redirect(`/oauth/consent?authorization_id=${id}&failed=1`);
  if (!("authorization_id" in details)) hostRedirect(details.redirect_url);
  if (details.client.id !== process.env.MCP_OAUTH_CLIENT_ID) throw new Error("Ez a kliens nincs engedélyezve.");
  const { data, error } = decision === "approve"
    ? await client.auth.oauth.approveAuthorization(id, { skipBrowserRedirect: true })
    : await client.auth.oauth.denyAuthorization(id, { skipBrowserRedirect: true });
  if (error || !data?.redirect_url) redirect(`/oauth/consent?authorization_id=${id}&failed=1`);
  hostRedirect(data.redirect_url);
}

export default async function ConsentPage({ searchParams }: {
  searchParams: Promise<{ authorization_id?: string; failed?: string }>;
}) {
  const params = await searchParams;
  const id = params.authorization_id;
  let message = "Hiányzó vagy érvénytelen kérés. Indítsd újra a kapcsolódást a ChatGPT-ben.";
  let details = null;
  if (validId(id)) {
    const client = await ownerClient(id);
    const result = await client.auth.oauth.getAuthorizationDetails(id);
    if (result.data && "redirect_url" in result.data) hostRedirect(result.data.redirect_url);
    if (result.data && "authorization_id" in result.data && result.data.client.id === process.env.MCP_OAUTH_CLIENT_ID) {
      details = result.data;
    } else message = "A kérés lejárt, érvénytelen, vagy nem az engedélyezett alkalmazástól érkezett.";
  }
  return <main className={styles.login}>
    <header className={styles.masthead}><strong>ContentOps</strong><span>Saját műhely</span></header>
    <section className={styles.consent}>
      <h1>Hozzáférés a műhelyedhez</h1>
      {!details ? <p role="alert">{message}</p> : <>
        <p><strong>{details.client.name}</strong> hozzáférést kér az ötleteidhez, a forrásaidhoz, a szövegeidhez és a hangprofilodhoz.</p>
        <p>A kapcsolat olvasni és módosítani tudja a műhely tartalmát, beleértve a verziókat és jóváhagyásokat. LinkedIn-posztot nem publikál.</p>
        <dl><dt>Bejelentkezett fiók</dt><dd>{details.user.email}</dd><dt>Kért azonosítási jogosultságok</dt><dd>{details.scope || "Nincs külön OIDC-jogosultság"}</dd><dt>Visszatérési cím</dt><dd>{details.redirect_uri}</dd></dl>
        {params.failed && <p role="alert">A döntést nem sikerült rögzíteni. Próbáld újra, vagy indíts új kapcsolatot.</p>}
        <form action={decide} className={styles.form}>
          <input type="hidden" name="authorization_id" value={id} />
          <button name="decision" value="approve">Hozzáférés engedélyezése</button>
          <button name="decision" value="deny">Elutasítás</button>
        </form>
      </>}
    </section>
  </main>;
}
