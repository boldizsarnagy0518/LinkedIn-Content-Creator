import { ContentOpsWorkspace } from "@/app/_components/contentops-workspace";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function HomePage() {
  const supabase = await createSupabaseServerClient();
  let claims = null;
  if (supabase) {
    claims = (await supabase.auth.getClaims()).data?.claims ?? null;
  }
  const accountLabel = typeof claims?.email === "string" ? claims.email : "Local workspace";

  return <ContentOpsWorkspace accountLabel={accountLabel} authEnabled={Boolean(supabase)} />;
}
