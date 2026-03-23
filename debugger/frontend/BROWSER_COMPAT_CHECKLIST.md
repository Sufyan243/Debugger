# Browser Compatibility Manual Checklist
**Version:** 1.0  
**Updated:** 2025  
**Use when:** Automated matrix CI is unavailable (emergency release gate).

---

## Browsers & Profiles to Test

| # | Browser | Version | Viewport |
|---|---------|---------|----------|
| 1 | Chrome (stable) | latest | 1440×900 desktop |
| 2 | Edge (stable) | latest | 1440×900 desktop |
| 3 | Firefox (stable) | latest | 1440×900 desktop |
| 4 | Chrome (mobile emulation) | latest | 390×844 (iPhone 14) |

---

## Checklist

For each browser/profile above, verify every item. Mark ✅ pass or ❌ fail with notes.

### Auth — Signup
- [ ] Sign-in button visible on load
- [ ] Auth modal opens on click
- [ ] "Continue with Email" navigates to email form
- [ ] Register tab shows password strength meter
- [ ] Mismatched passwords shows inline error, does not submit
- [ ] Valid signup shows "Check your inbox" pending screen
- [ ] Pending screen shows submitted email address

### Auth — Email Verification
- [ ] `/?verified=expired` shows expired-link notice banner
- [ ] `/?verified=error` shows invalid-link notice banner
- [ ] Notice banner dismisses on ✕ click
- [ ] `/?code=<valid>` triggers exchange and logs user in

### Auth — Login
- [ ] Wrong password shows error message in red box
- [ ] Correct credentials dismiss modal and show username/avatar in nav
- [ ] Logout button visible after login

### Auth — Logout & Relogin
- [ ] Logout clears username/avatar from nav
- [ ] Sign-in button reappears after logout
- [ ] Auth modal opens again after logout
- [ ] Relogin with same credentials succeeds

### OAuth Callbacks
- [ ] GitHub button redirects to GitHub (or shows config error if unconfigured)
- [ ] Google button redirects to Google (or shows config error if unconfigured)
- [ ] `/?code=` param is stripped from URL after exchange attempt

### Session Persistence (Refresh/Revisit)
- [ ] Reload while logged in keeps authenticated state (no sign-in button)
- [ ] Reload while anon keeps anon session (no new bootstrap visible in Network tab)
- [ ] Opening a new tab reuses existing session (check Network tab — no duplicate `/auth/anon`)

### Multi-Tab
- [ ] Logging out in Tab A and switching to Tab B: Tab B still shows previous state (no crash)
- [ ] No JS console errors across any scenario above

### Mobile Viewport (390×844)
- [ ] Auth modal fits within viewport without horizontal scroll
- [ ] All buttons are tappable (min 44×44 px touch target)
- [ ] Password show/hide toggle works on touch

---

## Sign-off

| Tester | Date | Browsers Tested | Result |
|--------|------|-----------------|--------|
|        |      |                 |        |
