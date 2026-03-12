import { useState } from "react";
import EditorPanel from "./components/Editor/EditorPanel";
import RunButton from "./components/Editor/RunButton";
import OutputPanel from "./components/Output/OutputPanel";
import { useExecute } from "./hooks/useExecute";

function App() {
  const [sessionId] = useState(() => {
    let id = localStorage.getItem("debugger_session_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("debugger_session_id", id);
    }
    return id;
  });

  const [code, setCode] = useState("");
  const [predictionEnabled, setPredictionEnabled] = useState(false);
  const [prediction, setPrediction] = useState("");
  const { state, result, isExecuting, sameCode, submittedPrediction, runCode, resetToIdle } = useExecute();

  const handleCodeChange = (v: string) => {
    resetToIdle();
    setCode(v);
  };

  return (
    <div style={{ background: "#1e1e2e", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <nav style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", height: 48, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        <span style={{ color: "#cdd6f4", fontWeight: 700 }}>⬡ Cognitive Debugger</span>
        <div style={{ display: "flex", gap: "24px" }}>
          <a style={{ color: "#cdd6f4", textDecoration: "none", cursor: "pointer" }}>Editor</a>
          <a style={{ color: "#585b70", textDecoration: "none", cursor: "pointer" }}>My Progress</a>
        </div>
      </nav>

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
            <OutputPanel state={state} result={result} prediction={submittedPrediction} sessionId={sessionId} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App
