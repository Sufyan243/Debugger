import { useState, useEffect, useRef } from "react";
import EditorPanel from "./components/Editor/EditorPanel";
import RunButton from "./components/Editor/RunButton";
import OutputPanel from "./components/Output/OutputPanel";
import DashboardPage from "./components/Dashboard/DashboardPage";
import AuthModal from "./components/Auth/AuthModal";
import { useExecute } from "./hooks/useExecute";
import { fetchMe, API_BASE } from "./api/client";

const USERNAME_KEY = "debugger_username";
const AVATAR_KEY = "debugger_avatar";
const SESSION_KEY = "debugger_session_id";
const ANON_KEY = "debugger_anon_id";

// JWT is held only in a React ref (in-memory) for logout revocation.
// It is never written to localStorage — the httpOnly cookie is the sole
// persistent session credential. Non-sensitive display metadata
// (username, avatar, session_id) is kept in localStorage for UI restoration.

const BASE = `${API_BASE}/api/v1`;

// ---------------------------------------------------------------------------
// JWT helpers
// ---------------------------------------------------------------------------

interface JwtPayload {
  sub: string;
  exp: number;
  anon?: boolean;
}

/** Returns the decoded payload or null on any parse/structure failure. */
function parseJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(parts[1].length / 4) * 4, "=");
    const payload = JSON.parse(atob(base64));
    if (typeof payload.sub !== "string" || !payload.sub) return null;
    if (typeof payload.exp !== "number") return null;
    return payload as JwtPayload;
  } catch {
    return null;
  }
}

/** Returns true only if the token is decodable, has a valid sub, and is not expired. */
function isTokenValid(token: string): boolean {
  const payload = parseJwtPayload(token);
  if (!payload) return false;
  return payload.exp * 1000 > Date.now();
}

/** Returns the sub from a valid token, or empty string on any failure. */
function getUserId(token: string): string {
  return parseJwtPayload(token)?.sub ?? "";
}

// ---------------------------------------------------------------------------
// OAuth param helper — reads once, no double-decode, never throws
// ---------------------------------------------------------------------------

interface OAuthParams {
  code: string;
  verified: string;
}

function getOAuthParams(): OAuthParams | null {
  try {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const verified = params.get("verified") ?? "";
    if (!code && !verified) return null;
    return { code: code ?? "", verified };
  } catch {
    return null;
  }
}

/** Clears all auth-related storage and strips auth query params from the URL. */
function clearAuthStorage() {
  [USERNAME_KEY, AVATAR_KEY, SESSION_KEY, ANON_KEY].forEach(k =>
    localStorage.removeItem(k)
  );
  // The httpOnly cookie is cleared server-side via POST /auth/logout.
}

function stripAuthParams() {
  try {
    const url = new URL(window.location.href);
    ["code", "verified"].forEach(p => url.searchParams.delete(p));
    window.history.replaceState({}, "", url.pathname + url.search);
  } catch {}
}

// ---------------------------------------------------------------------------
// Startup state initializers — run once synchronously before first render
// ---------------------------------------------------------------------------

function initUsername(): string {
  return localStorage.getItem(USERNAME_KEY) ?? "";
}

function initAvatar(): string {
  return localStorage.getItem(AVATAR_KEY) ?? "";
}

function initSessionId(): string {
  return localStorage.getItem(SESSION_KEY) ?? "";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function App() {
  const [jwt, setJwt] = useState<string>("");
  const jwtRef = useRef<string>(""); // in-memory only — used solely for logout revocation
  const [username, setUsername] = useState<string>(initUsername);
  const [avatar, setAvatar] = useState<string>(initAvatar);
  const [isAnon, setIsAnon] = useState<boolean>(true);
  const [authReady, setAuthReady] = useState<boolean>(false);
  const [showAuth, setShowAuth] = useState(false);
  const [verifiedNotice, setVerifiedNotice] = useState<"expired" | "error" | null>(null);
  const [view, setView] = useState<"editor" | "dashboard">("editor");
  const [code, setCode] = useState("");
  const [predictionEnabled, setPredictionEnabled] = useState(false);
  const [prediction, setPrediction] = useState("");
  const { state, result, isExecuting, error, sameCode, submittedPrediction, runCode, resetToIdle } = useExecute();

  const [sessionId, setSessionId] = useState<string>(initSessionId);

  // Version counter — increment to invalidate any in-flight anon bootstrap
  const anonReqVersion = useRef(0);

  // ---------------------------------------------------------------------------
  // Anon bootstrap — single guarded function used by mount and logout
  // ---------------------------------------------------------------------------

  function bootstrapAnon() {
    // Guard: if a real authenticated session is already established, don't overwrite it
    if (authReady && !isAnon) return;

    anonReqVersion.current += 1;
    const version = anonReqVersion.current;

    fetch(`${BASE}/auth/anon`, { method: "POST", credentials: "include" })
      .then(r => r.json())
      .then(data => {
        // Stale: a newer request started, or auth has been established since
        if (anonReqVersion.current !== version) return;
        if (!data.access_token) return;
        const anonId = getUserId(data.access_token);
        if (!anonId) return;
        // JWT held in ref only — not persisted to localStorage
        jwtRef.current = data.access_token;
        localStorage.setItem(ANON_KEY, anonId);
        localStorage.setItem(SESSION_KEY, anonId);
        setJwt(data.access_token);
        setIsAnon(true);
        setSessionId(anonId);
        setAuthReady(true);
      })
      .catch(() => { setAuthReady(true); });
  }

  // On mount: rehydrate from cookie first, then handle OAuth redirect or anon bootstrap
  useEffect(() => {
    const oauth = getOAuthParams();

    // OAuth redirect takes priority — skip rehydration and handle the code/error
    if (oauth) {
      if (oauth.verified === "expired" || oauth.verified === "error") {
        setVerifiedNotice(oauth.verified);
        stripAuthParams();
        setAuthReady(true);
        bootstrapAnon();
        return;
      }
      if (oauth.code) {
        fetch(`${BASE}/auth/exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ code: oauth.code }),
        })
          .then(r => r.json())
          .then(data => {
            if (data.access_token && isTokenValid(data.access_token)) {
              handleAuth(data.access_token, data.email ?? "", data.avatar_url ?? "");
            } else {
              clearAuthStorage();
              stripAuthParams();
              setAuthReady(true);
              bootstrapAnon();
            }
          })
          .catch(() => { stripAuthParams(); setAuthReady(true); bootstrapAnon(); });
        return;
      }
    }

    // No OAuth params — attempt cookie rehydration
    fetchMe().then(me => {
      if (me && !me.anon) {
        // Valid real-user cookie: restore authenticated state
        const storedUsername = localStorage.getItem(USERNAME_KEY) ?? me.email ?? "";
        const storedAvatar = localStorage.getItem(AVATAR_KEY) ?? me.avatar_url ?? "";
        setUsername(storedUsername);
        setAvatar(storedAvatar);
        setSessionId(me.sub);
        localStorage.setItem(SESSION_KEY, me.sub);
        setIsAnon(false);
        setAuthReady(true);
      } else if (me && me.anon) {
        // Valid anon cookie: restore anon session without creating a new one
        jwtRef.current = "";
        setSessionId(me.sub);
        localStorage.setItem(SESSION_KEY, me.sub);
        localStorage.setItem(ANON_KEY, me.sub);
        setIsAnon(true);
        setAuthReady(true);
      } else {
        // null → explicit 401/403: no valid cookie — bootstrap a fresh anon session
        setAuthReady(true);
        bootstrapAnon();
      }
    }).catch(() => {
      // Transient failure (5xx/network): keep whatever session state exists.
      // Do NOT call bootstrapAnon() — that would silently overwrite a real cookie.
      setAuthReady(true);
    });

    return () => { anonReqVersion.current += 1; };
  }, []);

  // ---------------------------------------------------------------------------
  // Auth handlers
  // ---------------------------------------------------------------------------

  async function handleAuth(token: string, emailOrUser: string, avatarUrl: string = "") {
    // Invalidate any in-flight anon bootstrap immediately
    anonReqVersion.current += 1;

    const anonId = localStorage.getItem(ANON_KEY);
    const userId = getUserId(token);

    // JWT held in ref only — not persisted to localStorage.
    // The httpOnly cookie (set by the backend exchange/login endpoint) is the
    // authoritative credential sent automatically on all requests.
    jwtRef.current = token;
    localStorage.setItem(USERNAME_KEY, emailOrUser);
    localStorage.setItem(AVATAR_KEY, avatarUrl);
    localStorage.setItem(SESSION_KEY, userId);
    setJwt(token);
    setUsername(emailOrUser);
    setAvatar(avatarUrl);
    setSessionId(userId);
    setIsAnon(false);
    setAuthReady(true);
    setShowAuth(false);
    stripAuthParams();

    if (anonId) {
      try {
        // Send both the cookie (automatic) and a Bearer header so merge
        // succeeds even when the cookie has not yet propagated across origins.
        const mergeRes = await fetch(`${BASE}/auth/merge`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({ anon_id: anonId }),
          credentials: "include",
        });
        if (mergeRes.status === 401 || mergeRes.status === 403) {
          handleSessionExpired();
          return;
        }
        // 400/409 = invalid or already-merged anon_id — stale key, clear it.
        if (mergeRes.status === 400 || mergeRes.status === 409) {
          localStorage.removeItem(ANON_KEY);
          return;
        }
        // Parse the body on any 2xx response.
        if (mergeRes.ok) {
          const mergeData = await mergeRes.json().catch(() => ({}));
          // merged: true              → successful, clear key.
          // merged: false, code=="merge_failed"   → transient DB failure,
          //                                          keep key for next login.
          // merged: false, any other code/absent  → terminal (already_merged,
          //                                          unknown), clear key.
          if (mergeData.merged === true) {
            localStorage.removeItem(ANON_KEY);
          } else if (mergeData.merged === false && mergeData.code !== "merge_failed") {
            localStorage.removeItem(ANON_KEY);
          }
          // code==="merge_failed" → keep ANON_KEY for retry on next login.
        }
      } catch {
        // Network failure — keep ANON_KEY for retry on next login.
      }
    }
  }

  function handleSessionExpired() {
    jwtRef.current = "";
    clearAuthStorage();
    setJwt("");
    setUsername("");
    setAvatar("");
    setSessionId("");
    setIsAnon(true);
    setShowAuth(true);
    bootstrapAnon();
  }

  async function handleLogout() {
    // Revoke the token server-side. Send the JWT from the in-memory ref as
    // Bearer if available; the backend also accepts the cookie as fallback.
    try {
      await fetch(`${BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
        ...(jwtRef.current
          ? { headers: { Authorization: `Bearer ${jwtRef.current}` } }
          : {}),
      });
    } catch {
      // Network failure — proceed with local logout anyway.
    }
    jwtRef.current = "";
    clearAuthStorage();
    setJwt("");
    setUsername("");
    setAvatar("");
    setSessionId("");
    setIsAnon(true);
    setView("editor");
    bootstrapAnon();
  }

  const handleCodeChange = (v: string) => {
    resetToIdle();
    setCode(v);
  };

  // Loading skeleton during fetchMe() rehydration — prevents flash of anon UI
  if (!authReady) {
    return (
      <div style={{ background: "#1e1e2e", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <div style={{
            width: 32, height: 32, border: "3px solid #313244",
            borderTopColor: "#6366f1", borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <span style={{ color: "#585b70", fontSize: 13 }}>Loading…</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: "#1e1e2e", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <nav className="app-nav">
        <span style={{ color: "#cdd6f4", fontWeight: 700 }}>Terra Debugger</span>
        <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
          {!isAnon && (
            <>
              <button
                onClick={() => setView("editor")}
                aria-current={view === "editor" ? "page" : undefined}
                style={{ background: "none", border: "none", color: view === "editor" ? "#cdd6f4" : "#585b70", cursor: "pointer", fontSize: 14, padding: 0 }}
              >
                Editor
              </button>
              <button
                onClick={() => setView("dashboard")}
                aria-current={view === "dashboard" ? "page" : undefined}
                style={{ background: "none", border: "none", color: view === "dashboard" ? "#cdd6f4" : "#585b70", cursor: "pointer", fontSize: 14, padding: 0 }}
              >
                My Progress
              </button>
            </>
          )}
          {isAnon ? (
            <button
              onClick={() => setShowAuth(true)}
              style={{ background: "#6366f1", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontWeight: 600, fontSize: 13, cursor: "pointer" }}
            >
              Sign in
            </button>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {avatar && <img src={avatar} alt="User avatar" style={{ width: 24, height: 24, borderRadius: "50%" }} />}
              <span style={{ color: "#585b70", fontSize: 12 }}>{username}</span>
              <button
                onClick={handleLogout}
                style={{ background: "none", border: "none", color: "#f38ba8", fontSize: 12, cursor: "pointer", padding: 0 }}
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </nav>

      {view === "editor" && (
        <div className="editor-shell">
          <div className="editor-pane">
            <div style={{ background: "#181825", padding: "12px 16px", borderBottom: "1px solid #313244", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "#cdd6f4", fontWeight: 600 }}>Python Editor</span>
              {isAnon && (
                <button
                  onClick={() => setShowAuth(true)}
                  style={{ background: "none", border: "none", color: "#6366f1", fontSize: 11, cursor: "pointer", textDecoration: "underline", padding: 0 }}
                >
                  Sign in to save progress
                </button>
              )}
            </div>
            <EditorPanel value={code} onChange={handleCodeChange} />
            <div className="toolbar-row">
              <span style={{ color: "#585b70", fontSize: 12 }}>Python 3.11</span>
              <button
                role="switch"
                aria-checked={predictionEnabled}
                aria-label="Predict before run"
                onClick={() => { setPredictionEnabled(!predictionEnabled); if (predictionEnabled) setPrediction(""); }}
                style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: 12, color: "#a6adc8", cursor: "pointer", background: "none", border: "none", padding: 0 }}
              >
                <span>Predict before run</span>
                <div aria-hidden="true" style={{ width: 34, height: 18, background: predictionEnabled ? "#3b82f6" : "#45475a", borderRadius: 9, position: "relative" }}>
                  <div style={{ width: 14, height: 14, background: "#fff", borderRadius: "50%", position: "absolute", top: 2, left: predictionEnabled ? 18 : 2, transition: "left 0.2s" }} />
                </div>
              </button>
              <RunButton
                onClick={() => runCode(code, sessionId, jwt, predictionEnabled && prediction.trim() ? prediction : null)}
                disabled={isExecuting || !sessionId}
                sessionUnavailable={!sessionId}
              />
            </div>
            {predictionEnabled && (
              <div style={{ background: "#181825", borderTop: "1px solid #313244", padding: "12px 16px" }}>
                <div style={{ color: "#a6adc8", fontSize: 12, marginBottom: 8, fontWeight: 600 }}>What do you expect this code to output?</div>
                <textarea
                  value={prediction}
                  onChange={(e) => setPrediction(e.target.value)}
                  placeholder="Describe your expected output"
                  maxLength={1000}
                  style={{ width: "100%", background: "#1e1e2e", border: "1px solid #313244", color: "#cdd6f4", borderRadius: 6, padding: "8px 10px", fontSize: 13, fontFamily: "system-ui", resize: "vertical", minHeight: 60 }}
                />
              </div>
            )}
            {sameCode && (
              <div style={{ background: "#181825", padding: "8px 16px", color: "#f0a500", fontSize: 12, borderTop: "1px solid #313244" }}>
                Your code has not changed. Modify it before re-running.
              </div>
            )}
          </div>

          <div className="output-pane">
            <div style={{ background: "#181825", padding: "12px 16px", borderBottom: "1px solid #313244" }}>
              <span style={{ color: "#cdd6f4", fontWeight: 600 }}>Output</span>
            </div>
            <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
              <OutputPanel state={state} result={result} prediction={submittedPrediction} submissionId={result?.submission_id ?? null} sessionId={sessionId} authToken={jwt} error={error} onSessionExpired={handleSessionExpired} />
            </div>
          </div>
        </div>
      )}

      {view === "dashboard" && !isAnon && (
        <DashboardPage sessionId={sessionId} ownerToken={jwt} tokenReady={true} />
      )}

      {showAuth && <AuthModal onAuth={handleAuth} onClose={() => setShowAuth(false)} />}
      {verifiedNotice && (
        <div style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", background: verifiedNotice === "expired" ? "#92400e" : "#7f1d1d", color: "#fef3c7", borderRadius: 8, padding: "12px 20px", fontSize: 14, zIndex: 100, display: "flex", alignItems: "center", gap: 16 }}>
          {verifiedNotice === "expired"
            ? "Verification link has expired. Please sign in and request a new verification email."
            : "Invalid verification link. Please sign in and request a new verification email."}
          <button onClick={() => setVerifiedNotice(null)} style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>✕</button>
        </div>
      )}
    </div>
  );
}
