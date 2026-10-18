// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ get: vi.fn(), save: vi.fn() }));
vi.mock("@/lib/contentops-api", () => ({ getAuthorMemory: api.get, saveAuthorMemory: api.save }));
vi.mock("@/app/_components/modal", () => ({ Modal: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
import { AuthorMemoryDialog } from "@/app/_components/author-memory";
beforeEach(() => {
  api.get.mockResolvedValue({ background: "Fejlesztő", past_posts: [], revision: "initial" });
  api.save.mockImplementation(async (value) => ({ ...value, revision: "saved" }));
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("saves background and a past post with the loaded revision", async () => {
  render(<AuthorMemoryDialog onClose={() => {}} />);
  fireEvent.click(await screen.findByRole("button", { name: /Korábbi poszt hozzáadása/ }));
  fireEvent.change(screen.getByLabelText("Cím"), { target: { value: "Korábbi írás" } });
  fireEvent.change(screen.getByLabelText("Poszt szövege"), { target: { value: "Az én hangom." } });
  fireEvent.click(screen.getByLabelText("Használja írásmintaként"));
  fireEvent.click(screen.getByRole("button", { name: "Profil és posztok mentése" }));
  await screen.findByRole("status");
  expect(api.save).toHaveBeenCalledWith(expect.objectContaining({ revision: "initial", past_posts: [
    { title: "Korábbi írás", body: "Az én hangom.", topics: "", use_as_example: false }
  ] }));
});
it("keeps edited text visible if saving fails", async () => {
  api.save.mockRejectedValue(new Error("A profil közben megváltozott."));
  render(<AuthorMemoryDialog onClose={() => {}} />);
  const background = await screen.findByLabelText("Szakmai háttér és témák");
  fireEvent.change(background, { target: { value: "Új szakmai háttér" } });
  fireEvent.click(screen.getByRole("button", { name: "Profil és posztok mentése" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("megváltozott"));
  expect((background as HTMLTextAreaElement).value).toBe("Új szakmai háttér");
});
