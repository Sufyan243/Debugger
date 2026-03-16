import { useState, useEffect } from "react";
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

const BASE = `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/api/v1`;

function isAnonToken(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.anon === true;
  } catch {
    return false;
  }
}

function getUserId(token: string): string {
  try {
    return JSON.parse(atob(token.split(".")[1])).sub;
  } catch {
    return crypto.randomUUID();
  }
}

export default function App() {
  const [jwt, setJwt] = useState<string>(() => localStorage.getItem(JWT_KEY) ?? "");
  const [username, setUsername] = useState<string>(() => localStorage.getItem(USERNAME_KEY) ?? "");
  const [avatar, setAvatar] = useState<string>(() => localStorage.getItem(AVATAR_KEY) ?? "");
  const [showAuth, setShowAuth] = useState(false);
  const [view, setView] = useState<"editor" | "dashboard">("editor");
  const [code, setCode] = useState("");
  const [predictionEnabled, setPredictionEnabled] = useState(false);
  const [prediction, setPrediction] = useState("");
  const { state, result, isExecuting, sameCode, submittedPrediction, runCode, resetToIdle } = useExecute();

  const isAnon = !jwt || isAnonToken(jwt);
  const sessionId = localStorage.getItem(SESSION_KEY) ?? crypto.randomUUID();

  // On mount: create anon session if no token at all
  useEffect(() => {
    if (!jwt) {
      fetch(`${BASE}/auth/anon`, { method: "POST" })
        .then(r => r.json())
        .then(data => {
          if (data.access_token) {
            const anonId = getUserId(data.access_token);
            localStorage.setItem(JWT_KEY, data.access_token);
            localStorage.setItem(ANON_KEY, anonId);
            localStorage.setItem(SESSION_KEY, anonId);
            setJwt(data.access_token);
          }
        })
        .catch(() => {});
    }
  }, []);

  // Handle OAuth redirect — token comes back in URL query param
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const email = params.get("email");
    const avatarUrl = params.get("avatar");
    if (token) {
      handleAuth(token, email ?? "", avatarUrl ?? "");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  async function handleAuth(token: string, emailOrUser: string, avatarUrl: string = "") {
    const anonId = localStorage.getItem(ANON_KEY);
    localStorage.setItem(JWT_KEY, token);
    localStorage.setItem(USERNAME_KEY, emailOrUser);
    localStorage.setItem(AVATAR_KEY, avatarUrl);
    localStorage.setItem(SESSION_KEY, getUserId(token));
    setJwt(token);
    setUsername(emailOrUser);
    setAvatar(avatarUrl);
    setShowAuth(false);

    // Merge anon session data into real account
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
    [JWT_KEY, USERNAME_KEY, AVATAR_KEY, SESSION_KEY, ANON_KEY].forEach(k => localStorage.removeItem(k));
    setJwt("");
    setUsername("");
    setAvatar("");
  }

  const handleCodeChange = (v: string) => {
    resetToIdle();
    setCode(v);
  };

  return (
    <div style={{ background: "#1e1e2e", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <nav style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", height: 48, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        <span style={{ color: "#cdd6f4", fontWeight: 700 }}>Cognitive Debugger</span>
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
              <RunButton onClick={() => runCode(code, sessionId, predictionEnabled && prediction.trim() ? prediction : null)} disabled={isExecuting} />
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
              <OutputPanel state={state} result={result} prediction={submittedPrediction} />
            </div>
          </div>
        </div>
      )}

      {view === "dashboard" && !isAnon && (
        <DashboardPage sessionId={sessionId} ownerToken={jwt} tokenReady={true} />
      )}

      {showAuth && <AuthModal onAuth={handleAuth} onClose={() => setShowAuth(false)} />}
    </div>
  );
}
