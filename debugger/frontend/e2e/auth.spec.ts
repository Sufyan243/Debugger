/**
 * E2E regression suite — auth lifecycle
 * Covers: signup, email verification, login, logout, relogin,
 *         OAuth callbacks, refresh/revisit, multi-tab session.
 *
 * Run: npx playwright test
 * Requires: VITE_API_BASE_URL set in .env (or via env var BASE_URL)
 */
import { test, expect, chromium, type Page, type BrowserContext } from "@playwright/test";

const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const API  = process.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function openAuthModal(page: Page) {
  await page.goto(BASE);
  await page.getByRole("button", { name: /sign in/i }).first().click();
  await expect(page.getByText("Welcome to Debugger")).toBeVisible();
}

async function goToEmailForm(page: Page, tab: "login" | "register" = "login") {
  await openAuthModal(page);
  await page.getByRole("button", { name: /continue with email/i }).click();
  if (tab === "register") {
    await page.getByRole("button", { name: /register/i }).click();
  }
}

async function fillAndSubmit(
  page: Page,
  email: string,
  password: string,
  confirm?: string,
) {
  await page.getByPlaceholder("you@example.com").fill(email);
  const pwFields = page.getByPlaceholder("••••••••");
  await pwFields.first().fill(password);
  if (confirm !== undefined) await pwFields.nth(1).fill(confirm);
  await page.getByRole("button", { name: /create account|sign in/i }).click();
}

// ---------------------------------------------------------------------------
// 1. Signup — happy path shows pending screen
// ---------------------------------------------------------------------------

test("signup with valid credentials shows verification pending screen", async ({ page }) => {
  await goToEmailForm(page, "register");
  await fillAndSubmit(page, "newuser@example.com", "Password1!", "Password1!");
  await expect(page.getByText(/check your inbox/i)).toBeVisible({ timeout: 8000 });
  await expect(page.getByText("newuser@example.com")).toBeVisible();
});

// ---------------------------------------------------------------------------
// 2. Signup — password mismatch shows inline error
// ---------------------------------------------------------------------------

test("signup with mismatched passwords shows error", async ({ page }) => {
  await goToEmailForm(page, "register");
  await fillAndSubmit(page, "mismatch@example.com", "Password1!", "Different1!");
  await expect(page.getByText(/passwords do not match/i)).toBeVisible();
});

// ---------------------------------------------------------------------------
// 3. Email verification — expired token shows expired notice
// ---------------------------------------------------------------------------

test("expired verification link shows expired notice", async ({ page }) => {
  await page.goto(`${BASE}/?verified=expired`);
  await expect(page.getByText(/verification link has expired/i)).toBeVisible({ timeout: 6000 });
});

// ---------------------------------------------------------------------------
// 4. Email verification — error token shows error notice
// ---------------------------------------------------------------------------

test("invalid verification link shows error notice", async ({ page }) => {
  await page.goto(`${BASE}/?verified=error`);
  await expect(page.getByText(/invalid verification link/i)).toBeVisible({ timeout: 6000 });
});

// ---------------------------------------------------------------------------
// 5. Login — wrong password shows error
// ---------------------------------------------------------------------------

test("login with wrong password shows error message", async ({ page }) => {
  await goToEmailForm(page, "login");
  await fillAndSubmit(page, "ghost@example.com", "WrongPass1!");
  await expect(page.locator("[style*='rgba(239,68,68']")).toBeVisible({ timeout: 6000 });
});

// ---------------------------------------------------------------------------
// 6. OAuth callback — GitHub redirect lands on app without crash
// ---------------------------------------------------------------------------

test("OAuth callback with verified=1 and code param strips params from URL", async ({ page }) => {
  // Simulate the post-OAuth redirect the backend sends back
  await page.route(`${API}/api/v1/auth/exchange`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "", email: "", avatar_url: "" }),
    });
  });
  await page.goto(`${BASE}/?code=testcode123`);
  // After exchange attempt, code param must be stripped
  await page.waitForTimeout(1500);
  expect(page.url()).not.toContain("code=");
});

// ---------------------------------------------------------------------------
// 7. Logout — clears authenticated state and shows Sign in button
// ---------------------------------------------------------------------------

test("logout clears session and shows sign-in button", async ({ page }) => {
  // Stub /auth/me to return a real user so the app thinks we're logged in
  await page.route(`${API}/api/v1/auth/me`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ sub: "user-1", anon: false, email: "u@example.com", avatar_url: null }),
    });
  });
  await page.route(`${API}/api/v1/auth/logout`, async route => {
    await route.fulfill({ status: 204, body: "" });
  });
  await page.goto(BASE);
  await expect(page.getByRole("button", { name: /logout/i })).toBeVisible({ timeout: 6000 });
  await page.getByRole("button", { name: /logout/i }).click();
  await expect(page.getByRole("button", { name: /sign in/i }).first()).toBeVisible({ timeout: 6000 });
});

// ---------------------------------------------------------------------------
// 8. Relogin — after logout, user can open auth modal again
// ---------------------------------------------------------------------------

test("after logout user can open auth modal and attempt relogin", async ({ page }) => {
  await page.route(`${API}/api/v1/auth/me`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ sub: "user-1", anon: false, email: "u@example.com", avatar_url: null }),
    });
  });
  await page.route(`${API}/api/v1/auth/logout`, async route => {
    await route.fulfill({ status: 204, body: "" });
  });
  await page.goto(BASE);
  await page.getByRole("button", { name: /logout/i }).click();
  await page.getByRole("button", { name: /sign in/i }).first().click();
  await expect(page.getByText("Welcome to Debugger")).toBeVisible({ timeout: 4000 });
});

// ---------------------------------------------------------------------------
// 9. Refresh/revisit — anon session is preserved across page reload
// ---------------------------------------------------------------------------

test("anon session is preserved on page reload (no new bootstrap)", async ({ page }) => {
  let anonCallCount = 0;
  await page.route(`${API}/api/v1/auth/anon`, async route => {
    anonCallCount++;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      // Minimal JWT-shaped token: header.payload.sig
      body: JSON.stringify({ access_token: "eyJ.eyJzdWIiOiJhbm9uLTEiLCJleHAiOjk5OTk5OTk5OTksImFub24iOnRydWV9.sig" }),
    });
  });
  await page.route(`${API}/api/v1/auth/me`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ sub: "anon-1", anon: true, email: null, avatar_url: null }),
    });
  });

  await page.goto(BASE);
  await page.waitForTimeout(1000);
  const firstCount = anonCallCount;

  await page.reload();
  await page.waitForTimeout(1000);

  // After reload, /auth/me returns the existing anon cookie — no new bootstrap
  expect(anonCallCount).toBe(firstCount);
});

// ---------------------------------------------------------------------------
// 10. Transient /auth/me failure — does NOT bootstrap anon (regression)
// ---------------------------------------------------------------------------

test("transient 503 from /auth/me does not trigger anon bootstrap", async ({ page }) => {
  let anonBootstrapped = false;
  await page.route(`${API}/api/v1/auth/me`, async route => {
    await route.fulfill({ status: 503, body: "Service Unavailable" });
  });
  await page.route(`${API}/api/v1/auth/anon`, async route => {
    anonBootstrapped = true;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "eyJ.eyJzdWIiOiJhbm9uLTEiLCJleHAiOjk5OTk5OTk5OTl9.sig" }),
    });
  });

  await page.goto(BASE);
  await page.waitForTimeout(1500);
  expect(anonBootstrapped).toBe(false);
});

// ---------------------------------------------------------------------------
// 12. Stale ANON_KEY — merge 200 {merged:false} clears key (regression)
// ---------------------------------------------------------------------------

test("merge 200 merged:false clears ANON_KEY from localStorage", async ({ page }) => {
  // Seed a stale anon id in localStorage before the app boots
  await page.goto(BASE);
  await page.evaluate(() => localStorage.setItem("debugger_anon_id", "stale-anon-uuid"));

  // Stub /auth/me to return a real user (triggers handleAuth path)
  await page.route(`${API}/api/v1/auth/me`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ sub: "user-1", anon: false, email: "u@example.com", avatar_url: null }),
    });
  });

  // Stub /auth/merge to return 200 with merged:false (already merged / not found)
  await page.route(`${API}/api/v1/auth/merge`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ merged: false, code: "already_merged" }),
    });
  });

  // Stub /auth/login so we can trigger handleAuth via the modal
  await page.route(`${API}/api/v1/auth/login`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "eyJ.eyJzdWIiOiJ1c2VyLTEiLCJleHAiOjk5OTk5OTk5OTl9.sig", email: "u@example.com", avatar_url: null }),
    });
  });

  await page.reload();
  await page.waitForTimeout(1000);

  // Open modal and log in to trigger handleAuth + merge
  await page.getByRole("button", { name: /sign in/i }).first().click();
  await page.getByRole("button", { name: /continue with email/i }).click();
  await page.getByPlaceholder("you@example.com").fill("u@example.com");
  await page.getByPlaceholder("\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022").first().fill("Password1!");
  await page.getByRole("button", { name: /sign in/i }).last().click();

  // Wait for merge to complete
  await page.waitForTimeout(1000);

  // ANON_KEY must be cleared even though merged was false
  const anonKey = await page.evaluate(() => localStorage.getItem("debugger_anon_id"));
  expect(anonKey).toBeNull();
});

// ---------------------------------------------------------------------------
// 13. Retryable merge failure — merged:false with retry reason keeps ANON_KEY
// ---------------------------------------------------------------------------

test("merge 200 merged:false with retry reason keeps ANON_KEY in localStorage", async ({ page }) => {
  await page.goto(BASE);
  await page.evaluate(() => localStorage.setItem("debugger_anon_id", "retryable-anon-uuid"));

  await page.route(`${API}/api/v1/auth/me`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ sub: "user-1", anon: false, email: "u@example.com", avatar_url: null }),
    });
  });

  // Backend transient failure: merged:false with retryable code
  await page.route(`${API}/api/v1/auth/merge`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ merged: false, code: "merge_failed" }),
    });
  });

  await page.route(`${API}/api/v1/auth/login`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "eyJ.eyJzdWIiOiJ1c2VyLTEiLCJleHAiOjk5OTk5OTk5OTl9.sig", email: "u@example.com", avatar_url: null }),
    });
  });

  await page.reload();
  await page.waitForTimeout(1000);

  await page.getByRole("button", { name: /sign in/i }).first().click();
  await page.getByRole("button", { name: /continue with email/i }).click();
  await page.getByPlaceholder("you@example.com").fill("u@example.com");
  await page.getByPlaceholder("\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022").first().fill("Password1!");
  await page.getByRole("button", { name: /sign in/i }).last().click();

  await page.waitForTimeout(1000);

  // ANON_KEY must be retained so the next login can retry the merge
  const anonKey = await page.evaluate(() => localStorage.getItem("debugger_anon_id"));
  expect(anonKey).toBe("retryable-anon-uuid");
});

// ---------------------------------------------------------------------------
// 11. Multi-tab — second tab reuses existing session, no duplicate bootstrap
// ---------------------------------------------------------------------------

test("second tab reuses existing anon session without new bootstrap", async ({ browser }) => {
  const context: BrowserContext = await browser.newContext();
  let anonCallCount = 0;

  await context.route(`${API}/api/v1/auth/anon`, async route => {
    anonCallCount++;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "eyJ.eyJzdWIiOiJhbm9uLTEiLCJleHAiOjk5OTk5OTk5OTl9.sig" }),
    });
  });
  await context.route(`${API}/api/v1/auth/me`, async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ sub: "anon-1", anon: true, email: null, avatar_url: null }),
    });
  });

  const tab1 = await context.newPage();
  await tab1.goto(BASE);
  await tab1.waitForTimeout(1000);
  const countAfterTab1 = anonCallCount;

  const tab2 = await context.newPage();
  await tab2.goto(BASE);
  await tab2.waitForTimeout(1000);

  // Tab 2 finds the existing anon cookie via /auth/me — no new bootstrap
  expect(anonCallCount).toBe(countAfterTab1);
  await context.close();
});
