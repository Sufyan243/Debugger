import { useState, useEffect } from "react";
import { postSolutionRequest, API_BASE } from "../../api/client";

interface SolutionGateProps {
  submissionId: string;
  sessionId: string;
  authToken: string;
  isVisible: boolean;
}

export default function SolutionGate({ submissionId, sessionId, authToken, isVisible }: SolutionGateProps) {
  const [requestCount, setRequestCount] = useState<number | null>(null);
  const [solutionText, setSolutionText] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Hydrate current state from the read-only GET endpoint — does NOT increment request_count.
  useEffect(() => {
    if (!isVisible || !submissionId) return;
    setError(null);
    fetch(
      `${API_BASE}/api/v1/solution-request/${submissionId}?session_id=${sessionId}`,
      { credentials: "include" }
    )
      .then(r => r.ok ? r.json() : null)
      .then(res => {
        if (!res) { setRequestCount(0); return; }
        setRequestCount(res.request_count);
        if (res.solution_revealed && res.solution_text) {
          setSolutionText(res.solution_text);
        }
      })
      .catch(() => setRequestCount(0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submissionId]);

  if (!isVisible) return null;
  if (requestCount === null) return null;

  const handleRequest = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await postSolutionRequest(submissionId, sessionId, authToken);
      setRequestCount(response.request_count);
      if (response.solution_revealed && response.solution_text) {
        setSolutionText(response.solution_text);
      }
      setDialogOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed. Please try again.");
      // Keep dialog open so the user can retry without losing their place.
    } finally {
      setIsLoading(false);
    }
  };

  const dialogContent = [
    {
      title: "Are you sure?",
      body: "Seeing the solution now means you miss the learning. Try once more?",
      cancel: "Try once more",
      confirm: "Yes, show me (1/3)",
    },
    {
      title: "Are you sure? (Request 2 of 3)",
      body: "One more attempt could be the breakthrough.",
      cancel: "Keep trying",
      confirm: "Yes, show me (2/3)",
    },
    {
      title: "Last confirmation (Request 3 of 3)",
      body: "The solution will now be revealed.",
      cancel: "Cancel",
      confirm: "Reveal solution",
    },
  ];

  const dialogIndex = Math.min(requestCount, 2);

  if (solutionText) {
    return (
      <div style={{ background: "#2d1f1a", border: "1px solid #f0a500", borderRadius: "8px", padding: "14px 16px", marginTop: "16px" }}>
        <div style={{ color: "#f0a500", fontSize: "12px", fontWeight: 700, textTransform: "uppercase", marginBottom: "8px" }}>
          Full Solution
        </div>
        <div style={{ color: "#cdd6f4", fontSize: "13px", lineHeight: 1.5 }}>{solutionText}</div>
      </div>
    );
  }

  return (
    <>
      {!dialogOpen && (
        <button
          onClick={() => { setError(null); setDialogOpen(true); }}
          style={{
            marginTop: "10px", background: "transparent", color: "#f38ba8",
            border: "1.5px solid #f38ba8", borderRadius: "5px", padding: "8px 14px",
            fontSize: "13px", fontWeight: 600, cursor: "pointer", width: "100%",
          }}
        >
          Show Solution
        </button>
      )}

      {dialogOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "#1e1e2e", border: "1px solid #313244", borderRadius: "8px", padding: "24px", maxWidth: "400px", width: "90%" }}>
            <div style={{ color: "#cdd6f4", fontSize: "18px", fontWeight: 700, marginBottom: "12px" }}>
              {dialogContent[dialogIndex].title}
            </div>
            <div style={{ color: "#a6adc8", fontSize: "14px", marginBottom: "20px" }}>
              {dialogContent[dialogIndex].body}
            </div>

            {error && (
              <div style={{ background: "rgba(243,139,168,0.1)", border: "1px solid #f38ba8", borderRadius: "6px", padding: "10px 12px", color: "#f38ba8", fontSize: "13px", marginBottom: "16px" }}>
                {error}
                <button
                  onClick={handleRequest}
                  disabled={isLoading}
                  style={{ display: "block", marginTop: "8px", background: "none", border: "none", color: "#f38ba8", fontSize: "12px", cursor: "pointer", padding: 0, textDecoration: "underline" }}
                >
                  Retry
                </button>
              </div>
            )}

            <div style={{ display: "flex", gap: "12px" }}>
              <button
                onClick={() => { setDialogOpen(false); setError(null); }}
                style={{ flex: 1, background: "#313244", color: "#cdd6f4", border: "none", borderRadius: "5px", padding: "10px", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
              >
                {dialogContent[dialogIndex].cancel}
              </button>
              <button
                onClick={handleRequest}
                disabled={isLoading}
                style={{ flex: 1, background: isLoading ? "#7a4a56" : "#f38ba8", color: "#1e1e2e", border: "none", borderRadius: "5px", padding: "10px", fontSize: "13px", fontWeight: 600, cursor: isLoading ? "not-allowed" : "pointer" }}
              >
                {isLoading ? "Loading…" : dialogContent[dialogIndex].confirm}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
