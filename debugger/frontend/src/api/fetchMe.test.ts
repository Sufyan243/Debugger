import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchMe } from "./client";

afterEach(() => vi.restoreAllMocks());

describe("fetchMe", () => {
  it("returns null on 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    await expect(fetchMe()).resolves.toBeNull();
  });

  it("returns null on 403", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }));
    await expect(fetchMe()).resolves.toBeNull();
  });

  it("throws on 503 (transient) so caller does NOT bootstrap anon", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    await expect(fetchMe()).rejects.toThrow("transient failure 503");
  });

  it("throws on 500 (transient)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(fetchMe()).rejects.toThrow("transient failure 500");
  });

  it("throws on network error (transient)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchMe()).rejects.toThrow();
  });

  it("returns MeResponse on 200", async () => {
    const me = { sub: "user-1", anon: false, email: "a@b.com", avatar_url: null };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => me }));
    await expect(fetchMe()).resolves.toEqual(me);
  });
});
