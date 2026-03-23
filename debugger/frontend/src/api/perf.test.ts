/**
 * Performance & resilience tests for useExecute and fetchMe.
 * Thresholds: repeat-action p95 < 200 ms, degraded-network < 3 s.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchMe } from "../api/client";

afterEach(() => vi.restoreAllMocks());

// ---------------------------------------------------------------------------
// Repeat-action latency — fetchMe called 50 times must complete in < 200 ms
// ---------------------------------------------------------------------------

describe("fetchMe repeat-action performance", () => {
  it("50 sequential calls complete in under 200 ms", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ sub: "u1", anon: false, email: "a@b.com", avatar_url: null }),
      }),
    );

    const start = performance.now();
    for (let i = 0; i < 50; i++) await fetchMe();
    const elapsed = performance.now() - start;

    expect(elapsed).toBeLessThan(200);
  });
});

// ---------------------------------------------------------------------------
// Degraded-network — fetchMe with 1 s artificial delay resolves within 3 s
// ---------------------------------------------------------------------------

describe("fetchMe degraded-network resilience", () => {
  it("resolves within 3 s under 1 s simulated network latency", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        () =>
          new Promise(resolve =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  status: 200,
                  json: async () => ({ sub: "u1", anon: false, email: null, avatar_url: null }),
                }),
              1000,
            ),
          ),
      ),
    );

    const start = performance.now();
    const result = await fetchMe();
    const elapsed = performance.now() - start;

    expect(result).not.toBeNull();
    expect(elapsed).toBeLessThan(3000);
  });

  it("throws (transient) within 3 s when server responds 503 after 1 s delay", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        () =>
          new Promise(resolve =>
            setTimeout(() => resolve({ ok: false, status: 503 }), 1000),
          ),
      ),
    );

    const start = performance.now();
    await expect(fetchMe()).rejects.toThrow("transient failure 503");
    expect(performance.now() - start).toBeLessThan(3000);
  });
});

// ---------------------------------------------------------------------------
// Transient-failure — 503 must never call bootstrapAnon (integration guard)
// ---------------------------------------------------------------------------

describe("fetchMe transient failure contract", () => {
  it("throws on 500 so callers can skip anon bootstrap", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(fetchMe()).rejects.toThrow();
  });

  it("returns null on 401 so callers can bootstrap anon", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    await expect(fetchMe()).resolves.toBeNull();
  });
});
