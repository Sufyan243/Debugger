import { useState } from "react";
import EditorPanel from "./components/Editor/EditorPanel";
import RunButton from "./components/Editor/RunButton";
import OutputPanel from "./components/Output/OutputPanel";
import DashboardPage from "./components/Dashboard/DashboardPage";
import LoginPage from "./components/Auth/LoginPage";
import { useExecute } from "./hooks/useExecute";

const JWT_KEY = "debugger_jwt";
const USERNAME_KEY = "debugger_username";
const SESSION_KEY = "debugger_session_id";

function App() {
  const [jwt, setJwt] = useState<string>(() => localStorage.getItem(JWT_KEY) ?? "");
  const [username, setUsername] = useState<string>(() => localStorage.getItem(USERNAME_KEY) ?? "");

  const sessionId = (() => {
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) { id = crypto.randomUUID(); localStorage.setItem(SESSION_KEY, id); }
    return id;
  })();

  function handleAuth(token: string, user: string) {
    localStorage.setItem(JWT_KEY, token);
    localStorage.setItem(USERNAME_KEY, user);
    setJwt(token);
    setUsername(user);
  }

  function handleLogout() {
    localStorage.removeItem(JWT_KEY);
    localStorage.removeItem(USERNAME_KEY);
    setJwt("");
    setUsername("");
  }

  const [view, setView] = useState<"editor" | "dashboard">("editor");
  const [code, setCode] = useState("");
  const [predictionEnabled, setPredictionEnabled] = useState(false);
  const [prediction, setPrediction] = useState("");
  const { state, result, isExecuting, sameCode, submittedPrediction, runCode, resetToIdle } = useExecute();

  if (!jwt) return <LoginPage onAuth={handleAuth} />;

  const handleCodeChange = (v: string) => {
    resetToIdle();
    setCode(v);
  };

  return (
    <div style={{ background: "#1e1e2e", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <nav style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", height: 48, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        <span style={{ color: "#cdd6f4", fontWeight: 700 }}>⬡ Cognitive Debugger</span>
        <div style={{ display: "flex", gap: "24px", alignItems: "center" }}>
          <a style={{ color: view === "editor" ? "#cdd6f4" : "#585b70", textDecoration: "none", cursor: "pointer" }} onClick={() => setView("editor")}>Editor</a>
          <a style={{ color: view === "dashboard" ? "#cdd6f4" : "#585b70", textDecoration: "none", cursor: "pointer" }} onClick={() => setView("dashboard")}>My Progress</a>
          <span style={{ color: "#585b70", fontSize: 12 }}>{username}</span>
          <a style={{ color: "#f38ba8", fontSize: 12, cursor: "pointer" }} onClick={handleLogout}>Logout</a>
        </div>
      </nav>

      {view === "editor" && (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", flex: 1, height: "calc(100vh - 48px)" }}>
        <div style={{ display: "flex", flexDirection: "column", background: "#1e1e2e" }}>
          <div style={{ background: "#181825", padding: "12px 16px", borderBottom: "1px solid #313244", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#cdd6f4", fontWeight: 600 }}>Python Editor</span>
            <span style={{ color: "#585b70", fontSize: 11 }}>session: {sessionId.slice(0, 8)}…</span>
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
                placeholder="Describe your expected output…"
                maxLength={1000}
                style={{ width: "100%", background: "#1e1e2e", border: "1px solid #313244", color: "#cdd6f4", borderRadius: 6, padding: "8px 10px", fontSize: 13, fontFamily: "system-ui", resize: "vertical", minHeight: 60 }}
              />
            </div>
          )}
          {sameCode && (
            <div style={{ background: "#181825", padding: "8px 16px", color: "#f0a500", fontSize: 12, borderTop: "1px solid #313244" }}>
              ⚠ Your code hasn't changed. Modify it before re-running.
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
      {view === "dashboard" && <DashboardPage sessionId={sessionId} ownerToken={jwt} tokenReady={true} />}
    </div>
  );
}

export default App
