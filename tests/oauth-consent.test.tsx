// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ user: vi.fn(), details: vi.fn(), approve: vi.fn(), deny: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createSupabaseServerClient: async () => ({ auth: {
  getUser: mocks.user, oauth: { getAuthorizationDetails: mocks.details, approveAuthorization: mocks.approve, denyAuthorization: mocks.deny }
} }) }));
vi.mock("next/navigation", () => ({ redirect: (path: string) => { throw new Error(`REDIRECT:${path}`); } }));
import ConsentPage from "@/app/oauth/consent/page";

beforeEach(() => {
  vi.stubEnv("CONTENTOPS_OWNER_USER_ID", "owner");
  vi.stubEnv("MCP_OAUTH_CLIENT_ID", "client");
  mocks.user.mockResolvedValue({ data: { user: { id: "owner" } }, error: null });
  mocks.details.mockResolvedValue({ data: {
    authorization_id: "request-1", client: { id: "client", name: "ContentOps ChatGPT" },
    user: { email: "owner@example.test" }, scope: "openid email", redirect_uri: "https://chatgpt.com/callback"
  }, error: null });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); vi.unstubAllEnvs(); });

it("shows explicit consent and never approves during page load", async () => {
  render(await ConsentPage({ searchParams: Promise.resolve({ authorization_id: "request-1" }) }));
  expect(screen.getByRole("button", { name: "Hozzáférés engedélyezése" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Elutasítás" })).toBeTruthy();
  expect(mocks.approve).not.toHaveBeenCalled();
});
it("preserves the authorization request when the session expired", async () => {
  mocks.user.mockResolvedValue({ data: { user: null }, error: null });
  await expect(ConsentPage({ searchParams: Promise.resolve({ authorization_id: "request-1" }) }))
    .rejects.toThrow("REDIRECT:/login?next=%2Foauth%2Fconsent%3Fauthorization_id%3Drequest-1");
});
it("refuses a different owner before loading consent details", async () => {
  mocks.user.mockResolvedValue({ data: { user: { id: "stranger" } }, error: null });
  await expect(ConsentPage({ searchParams: Promise.resolve({ authorization_id: "request-1" }) }))
    .rejects.toThrow("Csak a műhely tulajdonosa");
  expect(mocks.details).not.toHaveBeenCalled();
});
it("refuses an unregistered client", async () => {
  mocks.details.mockResolvedValue({ data: { authorization_id: "request-1", client: { id: "stranger" } } });
  render(await ConsentPage({ searchParams: Promise.resolve({ authorization_id: "request-1" }) }));
  expect(screen.queryByRole("button", { name: "Hozzáférés engedélyezése" })).toBeNull();
  expect(screen.getByRole("alert").textContent).toContain("nem az engedélyezett");
});
