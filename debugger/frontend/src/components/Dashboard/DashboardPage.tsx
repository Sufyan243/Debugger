import { useState } from "react";
import { useDashboard } from "../../hooks/useDashboard";
import { fetchSessionHistory, SessionHistoryItem } from "../../api/client";
import ConceptBarChart from "./ConceptBarChart";

interface DashboardPageProps {
  sessionId: string;
  ownerToken: string;
  tokenReady: boolean;
}

export default function DashboardPage({ sessionId, ownerToken, tokenReady }: DashboardPageProps) {
  const { loading, error, conceptStats, weaknessProfile, sessionSummary, metacognitive, refresh } = useDashboard(sessionId, ownerToken);
  const [historyItems, setHistoryItems] = useState<SessionHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyQuery, setHistoryQuery] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);

  async function loadHistory(q = "") {
    setHistoryLoading(true);
    try {
      const res = await fetchSessionHistory(sessionId, ownerToken, q);
      setHistoryItems(res.items);
      setHistoryTotal(res.total);
    } catch { /* ignore */ } finally {
      setHistoryLoading(false);
    }
  }

  if (!tokenReady) {
    return (
      <div style={{ padding: 32, color: "#585b70", fontSize: 14, textAlign: "center" }}>
        Initializing session…
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: 32, color: "#585b70", fontSize: 14, textAlign: "center" }}>
        Loading dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 32, color: "#f38ba8", fontSize: 14, textAlign: "center" }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ background: "#1e1e2e", minHeight: "100%", padding: "24px", overflowY: "auto" }}>
      <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#cdd6f4", fontWeight: 700, fontSize: 18 }}>My Progress</span>
          <button
            onClick={refresh}
            style={{ background: "#313244", color: "#cdd6f4", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, cursor: "pointer" }}
          >
            Refresh
          </button>
        </div>

        {/* Section 1: Session Summary */}
        <div style={{ background: "#181825", borderRadius: 8, border: "1px solid #313244", padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 16 }}>
            Session Summary
          </div>
          <div className="stats-grid">
            {[
              { label: "Submissions", value: sessionSummary?.submissions_count ?? "—" },
              { label: "Errors", value: sessionSummary?.errors_count ?? "—" },
              { label: "Hints Used", value: sessionSummary?.hints_used ?? "—" },
              { label: "Concepts Learned", value: sessionSummary?.concepts_learned ?? "—" },
            ].map(({ label, value }) => (
              <div key={label} style={{ background: "#1e1e2e", borderRadius: 6, border: "1px solid #313244", padding: "14px 16px", textAlign: "center" }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: "#cdd6f4" }}>{value}</div>
                <div style={{ fontSize: 11, color: "#585b70", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ background: "#1e1e2e", borderRadius: 6, border: "1px solid #313244", padding: "12px 16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 12, color: "#a6adc8" }}>Prediction Accuracy</span>
            <span style={{ fontSize: 18, fontWeight: 700, color: "#89b4fa" }}>
              {sessionSummary ? `${(sessionSummary.prediction_accuracy * 100).toFixed(1)}%` : "—"}
            </span>
          </div>
        </div>

        {/* Section 2: Concept Mastery */}
        <div style={{ background: "#181825", borderRadius: 8, border: "1px solid #313244", padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 16 }}>
            Concept Mastery
          </div>
          {!conceptStats || conceptStats.concepts.length === 0 ? (
            <div style={{ color: "#585b70", fontSize: 13 }}>No concept data yet.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {conceptStats.concepts.map((item) => {
                // mastery = 1 - (error_count / attempts) * 100
                // attempts = total submissions in the session window (not error rows),
                // so a concept with 2 errors out of 10 submissions = 80% mastery.
                const mastery = Math.max(0, 100 - (item.error_count / Math.max(item.attempts, 1)) * 100);
                return (
                  <div key={item.concept}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, color: "#cdd6f4" }}>{item.concept}</span>
                      <span style={{ fontSize: 12, color: "#a6adc8" }}>{mastery.toFixed(0)}%</span>
                    </div>
                    <div style={{ background: "#313244", borderRadius: 4, height: 8, width: "100%" }}>
                      <div style={{ width: `${mastery}%`, height: "100%", background: "#a6e3a1", borderRadius: 4, transition: "width 0.3s" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Section 3: Weakness Areas */}
        <div style={{ background: "#181825", borderRadius: 8, border: "1px solid #313244", padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 16 }}>
            Weakness Areas
          </div>
          {!weaknessProfile || weaknessProfile.weak_concepts.length === 0 ? (
            <div style={{ color: "#a6e3a1", fontSize: 13 }}>No weak areas detected 🎉</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {weaknessProfile.weak_concepts.map((item) => (
                <div key={item.concept} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "#1e1e2e", borderRadius: 6, border: "1px solid #313244" }}>
                  <span style={{ fontSize: 13, color: "#cdd6f4" }}>{item.concept}</span>
                  <span style={{ fontSize: 11, fontWeight: 700, background: "#f38ba8", color: "#1e1e2e", borderRadius: 4, padding: "2px 8px" }}>
                    {item.error_count} errors
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section 4: Prediction Accuracy */}
        <div style={{ background: "#181825", borderRadius: 8, border: "1px solid #313244", padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 16 }}>
            Prediction Accuracy
          </div>
          {!metacognitive ? (
            <div style={{ color: "#585b70", fontSize: 13 }}>No prediction data yet. Enable predictions when running code.</div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
              <div style={{ fontSize: 48, fontWeight: 700, color: "#89b4fa" }}>
                {(metacognitive.accuracy_score * 100).toFixed(1)}%
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ fontSize: 12, color: "#a6adc8" }}>
                  Total Predictions: <span style={{ color: "#cdd6f4", fontWeight: 600 }}>{metacognitive.total_predictions}</span>
                </div>
                <div style={{ fontSize: 12, color: "#a6adc8" }}>
                  Correct: <span style={{ color: "#a6e3a1", fontWeight: 600 }}>{metacognitive.correct_predictions}</span>
                </div>
                <div style={{ fontSize: 12, color: "#a6adc8" }}>
                  Incorrect: <span style={{ color: "#f38ba8", fontWeight: 600 }}>{metacognitive.total_predictions - metacognitive.correct_predictions}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 5: Errors per Concept Chart */}
        <div style={{ background: "#181825", borderRadius: 8, border: "1px solid #313244", padding: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 16 }}>
            Errors per Concept
          </div>
          <ConceptBarChart data={conceptStats?.concepts ?? []} />
        </div>

        {/* Section 6: Session History (FR19 / FR20) */}
        <div style={{ background: "#181825", borderRadius: 8, border: "1px solid #313244", padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Session History
            </div>
            <button
              onClick={() => loadHistory(historyQuery)}
              style={{ background: "#313244", color: "#cdd6f4", border: "none", borderRadius: 6, padding: "4px 12px", fontSize: 12, cursor: "pointer" }}
            >
              Load
            </button>
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              value={historyQuery}
              onChange={e => setHistoryQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && loadHistory(historyQuery)}
              placeholder="Search code or concept…"
              style={{ flex: 1, background: "#1e1e2e", border: "1px solid #313244", color: "#cdd6f4", borderRadius: 6, padding: "6px 10px", fontSize: 13 }}
            />
            <button
              onClick={() => loadHistory(historyQuery)}
              style={{ background: "#6366f1", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 13, cursor: "pointer" }}
            >
              Search
            </button>
          </div>
          {historyLoading && <div style={{ color: "#585b70", fontSize: 13 }}>Loading…</div>}
          {!historyLoading && historyItems.length === 0 && (
            <div style={{ color: "#585b70", fontSize: 13 }}>No history yet. Click Load to fetch your sessions.</div>
          )}
          {!historyLoading && historyItems.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ color: "#585b70", fontSize: 11, marginBottom: 4 }}>{historyTotal} total submissions</div>
              {historyItems.map(item => (
                <div key={item.submission_id} style={{ background: "#1e1e2e", borderRadius: 6, border: `1px solid ${item.success ? "#1e3a2e" : "#3e2a2e"}`, padding: "10px 12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: item.success ? "#a6e3a1" : "#f38ba8", fontWeight: 700 }}>
                      {item.success ? "✓ Success" : `✗ ${item.exception_type ?? "Error"}`}
                    </span>
                    <span style={{ fontSize: 11, color: "#585b70" }}>
                      {new Date(item.timestamp).toLocaleString()}
                    </span>
                  </div>
                  {item.concept_category && (
                    <div style={{ fontSize: 11, color: "#cba6f7", marginBottom: 4 }}>{item.concept_category}</div>
                  )}
                  <pre style={{ margin: 0, fontSize: 11, color: "#a6adc8", fontFamily: "monospace", whiteSpace: "pre-wrap", overflow: "hidden", maxHeight: 48 }}>
                    {item.code_snippet}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
