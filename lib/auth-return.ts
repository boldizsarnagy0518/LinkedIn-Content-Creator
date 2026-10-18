/** Only explicitly supported local destinations may survive a login redirect. */
export function safeReturnPath(value: string | null | undefined): string {
  if (!value) return "/";
  try {
    const url = new URL(value, "https://contentops.invalid");
    if (url.origin !== "https://contentops.invalid") return "/";
    if (url.pathname === "/oauth/consent") {
      const id = url.searchParams.get("authorization_id");
      if (id && /^[a-zA-Z0-9_-]{1,128}$/.test(id)) return `/oauth/consent?authorization_id=${encodeURIComponent(id)}`;
    }
  } catch { /* Invalid or unsupported destinations return to the workspace. */ }
  return "/";
}
