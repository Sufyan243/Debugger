import { useState, useEffect, useRef } from "react";
import EditorPanel from "./components/Editor/EditorPanel";
import RunButton from "./components/Editor/RunButton";
import OutputPanel from "./components/Output/OutputPanel";
import DashboardPage from "./components/Dashboard/DashboardPage";
import AuthModal from "./components/Auth/AuthModal";
import { useExecute } from "./hooks/useExecute";

const JWT_KEY = "debugger_jwt";
const USERNAME_KEY = "debugger_username";
const AVATAR_KEY = "debugger_avatar";
const SESSION_KEY = "debugger_session_id";
const ANON_KEY = "debugger_anon_id";

const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1`;

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

/** Returns true if the token is a valid anon token. Never throws. */
function isAnonToken(token: string): boolean {
  const payload = parseJwtPayload(token);
  return payload !== null && payload.anon === true;
}

/** Returns the sub from a valid token, or empty string on any failure. */
function getUserId(token: string): string {
  return parseJwtPayload(token)?.sub ?? "";
}

// ---------------------------------------------------------------------------
// OAuth param helper — reads once, no double-decode, never throws
// ---------------------------------------------------------------------------

interface OAuthParams {
  token: string;
  email: string;
  avatar: string;
  verified: string;
}

function getOAuthParams(): OAuthParams | null {
  try {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const verified = params.get("verified") ?? "";
    if (!token && !verified) return null;
    // URLSearchParams.get() already percent-decodes — no further decode needed
    return {
      token: token ?? "",
      email: params.get("email") ?? "",
      avatar: params.get("avatar") ?? "",
      verified,
    };
  } catch {
    return null;
  }
}

/** Clears all auth-related storage and strips auth query params from the URL. */
function clearAuthStorage() {
  [JWT_KEY, USERNAME_KEY, AVATAR_KEY, SESSION_KEY, ANON_KEY].forEach(k =>
    localStorage.removeItem(k)
  );
}

function stripAuthParams() {
  try {
    const url = new URL(window.location.href);
    ["token", "email", "avatar", "verified"].forEach(p => url.searchParams.delete(p));
    window.history.replaceState({}, "", url.pathname + url.search);
  } catch {}
}

// ---------------------------------------------------------------------------
// Startup state initializers — run once synchronously before first render
// ---------------------------------------------------------------------------

function initJwt(): string {
  const oauth = getOAuthParams();
  if (oauth && oauth.token) {
    if (isTokenValid(oauth.token)) return oauth.token;
    // Invalid URL token — clear storage and stay anon
    clearAuthStorage();
    stripAuthParams();
    return "";
  }
  const stored = localStorage.getItem(JWT_KEY) ?? "";
  if (stored && isTokenValid(stored)) return stored;
  if (stored) {
    // Expired/malformed stored token — clear it
    clearAuthStorage();
  }
  return "";
}

function initUsername(): string {
  const oauth = getOAuthParams();
  if (oauth && oauth.token && isTokenValid(oauth.token)) return oauth.email;
  return localStorage.getItem(USERNAME_KEY) ?? "";
}

function initAvatar(): string {
  const oauth = getOAuthParams();
  if (oauth && oauth.token && isTokenValid(oauth.token)) return oauth.avatar;
  return localStorage.getItem(AVATAR_KEY) ?? "";
}

function initSessionId(): string {
  const oauth = getOAuthParams();
  if (oauth && oauth.token && isTokenValid(oauth.token)) return getUserId(oauth.token);
  return localStorage.getItem(SESSION_KEY) ?? "";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function App() {
  const [jwt, setJwt] = useState<string>(initJwt);
  const [username, setUsername] = useState<string>(initUsername);
  const [avatar, setAvatar] = useState<string>(initAvatar);
  const [showAuth, setShowAuth] = useState(false);
  const [verifiedNotice, setVerifiedNotice] = useState<"expired" | "error" | null>(null);
  const [view, setView] = useState<"editor" | "dashboard">("editor");
  const [code, setCode] = useState("");
  const [predictionEnabled, setPredictionEnabled] = useState(false);
  const [prediction, setPrediction] = useState("");
  const { state, result, isExecuting, sameCode, submittedPrediction, runCode, resetToIdle } = useExecute();

  const isAnon = !jwt || isAnonToken(jwt);
  const [sessionId, setSessionId] = useState<string>(initSessionId);

  // Version counter — increment to invalidate any in-flight anon bootstrap
  const anonReqVersion = useRef(0);

  // ---------------------------------------------------------------------------
  // Anon bootstrap — single guarded function used by mount and logout
  // ---------------------------------------------------------------------------

  function bootstrapAnon() {
    anonReqVersion.current += 1;
    const version = anonReqVersion.current;

    fetch(`${BASE}/auth/anon`, { method: "POST" })
      .then(r => r.json())
      .then(data => {
        // Stale: a newer request started, or auth has been established since
        if (anonReqVersion.current !== version) return;
        if (!data.access_token) return;
        const anonId = getUserId(data.access_token);
        if (!anonId) return;
        localStorage.setItem(JWT_KEY, data.access_token);
        localStorage.setItem(ANON_KEY, anonId);
        localStorage.setItem(SESSION_KEY, anonId);
        setJwt(data.access_token);
        setSessionId(anonId);
      })
      .catch(() => {});
  }

  // On mount: handle OAuth redirect, then bootstrap anon if needed
  useEffect(() => {
    const oauth = getOAuthParams();
    if (oauth) {
      if (oauth.verified === "expired" || oauth.verified === "error") {
        setVerifiedNotice(oauth.verified);
        stripAuthParams();
        bootstrapAnon();
        return;
      }
      if (isTokenValid(oauth.token)) {
        // State already initialised synchronously — just persist and merge
        handleAuth(oauth.token, oauth.email, oauth.avatar);
      } else {
        clearAuthStorage();
        stripAuthParams();
        bootstrapAnon();
      }
      return;
    }

    // No OAuth params — use stored session or create anon
    const existingSession = localStorage.getItem(SESSION_KEY);
    if (existingSession) {
      setSessionId(existingSession);
      return;
    }
    bootstrapAnon();

    // Invalidate any pending anon request on unmount
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

    localStorage.setItem(JWT_KEY, token);
    localStorage.setItem(USERNAME_KEY, emailOrUser);
    localStorage.setItem(AVATAR_KEY, avatarUrl);
    localStorage.setItem(SESSION_KEY, userId);
    setJwt(token);
    setUsername(emailOrUser);
    setAvatar(avatarUrl);
    setSessionId(userId);
    setShowAuth(false);
    stripAuthParams();

    if (anonId) {
      try {
        await fetch(`${BASE}/auth/merge`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ anon_id: anonId }),
        });
        localStorage.removeItem(ANON_KEY);
      } catch {}
    }
  }

  function handleLogout() {
    clearAuthStorage();
    setJwt("");
    setUsername("");
    setAvatar("");
    setSessionId("");
    setView("editor");
    bootstrapAnon();
  }

  const handleCodeChange = (v: string) => {
    resetToIdle();
    setCode(v);
  };

  return (
    <div style={{ background: "#1e1e2e", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <nav style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", height: 48, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        <span style={{ color: "#cdd6f4", fontWeight: 700 }}>Terra Debugger</span>
        <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
          {!isAnon && (
            <>
              <a style={{ color: view === "editor" ? "#cdd6f4" : "#585b70", textDecoration: "none", cursor: "pointer", fontSize: 14 }} onClick={() => setView("editor")}>Editor</a>
              <a style={{ color: view === "dashboard" ? "#cdd6f4" : "#585b70", textDecoration: "none", cursor: "pointer", fontSize: 14 }} onClick={() => setView("dashboard")}>My Progress</a>
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
              {avatar && <img src={avatar} alt="" style={{ width: 24, height: 24, borderRadius: "50%" }} />}
              <span style={{ color: "#585b70", fontSize: 12 }}>{username}</span>
              <a style={{ color: "#f38ba8", fontSize: 12, cursor: "pointer" }} onClick={handleLogout}>Logout</a>
            </div>
          )}
        </div>
      </nav>

      {view === "editor" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", flex: 1, height: "calc(100vh - 48px)" }}>
          <div style={{ display: "flex", flexDirection: "column", background: "#1e1e2e" }}>
            <div style={{ background: "#181825", padding: "12px 16px", borderBottom: "1px solid #313244", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "#cdd6f4", fontWeight: 600 }}>Python Editor</span>
              {isAnon && (
                <span
                  style={{ color: "#6366f1", fontSize: 11, cursor: "pointer", textDecoration: "underline" }}
                  onClick={() => setShowAuth(true)}
                >
                  Sign in to save progress
                </span>
              )}
            </div>
            <EditorPanel value={code} onChange={handleCodeChange} />
            <div style={{ background: "#181825", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
              <span style={{ color: "#585b70", fontSize: 12 }}>Python 3.11</span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: 12, color: "#a6adc8", cursor: "pointer" }} onClick={() => { setPredictionEnabled(!predictionEnabled); if (predictionEnabled) setPrediction(""); }}>
                <span>Predict before run</span>
                <div style={{ width: 34, height: 18, background: predictionEnabled ? "#3b82f6" : "#45475a", borderRadius: 9, position: "relative" }}>
                  <div style={{ width: 14, height: 14, background: "#fff", borderRadius: "50%", position: "absolute", top: 2, left: predictionEnabled ? 18 : 2, transition: "left 0.2s" }}></div>
                </div>
              </div>
              <RunButton onClick={() => runCode(code, sessionId, predictionEnabled && prediction.trim() ? prediction : null)} disabled={isExecuting || !sessionId} />
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

          <div style={{ background: "#181825", borderLeft: "1px solid #313244", display: "flex", flexDirection: "column" }}>
            <div style={{ background: "#181825", padding: "12px 16px", borderBottom: "1px solid #313244" }}>
              <span style={{ color: "#cdd6f4", fontWeight: 600 }}>Output</span>
            </div>
            <div style={{ flex: 1, padding: 16, overflow: "auto" }}>
              <OutputPanel state={state} result={result} prediction={submittedPrediction} submissionId={result?.submission_id ?? null} sessionId={sessionId} />
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
