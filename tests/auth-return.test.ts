import { describe, expect, it } from "vitest";
import { safeReturnPath } from "@/lib/auth-return";

describe("login return destination", () => {
  it("preserves the OAuth authorization ID across login", () => {
    expect(safeReturnPath("/oauth/consent?authorization_id=abc-123&ignored=1"))
      .toBe("/oauth/consent?authorization_id=abc-123");
  });
  it.each(["https://evil.test", "//evil.test/oauth/consent?authorization_id=a", "/\\evil.test", "/login", "/oauth/consent?authorization_id=../bad", null])("rejects unsafe or unsupported return paths: %s", (path) => {
    expect(safeReturnPath(path)).toBe("/");
  });
});
