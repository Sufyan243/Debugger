import { useState } from "react";

interface SolutionGateProps {
  submissionId: string;
  sessionId: string;
  isVisible: boolean;
}

export default function SolutionGate({ submissionId, sessionId, isVisible }: SolutionGateProps) {
  const [requestCount, setRequestCount] = useState(0);
  const [solutionText, setSolutionText] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  if (!isVisible) return null;

  const handleRequest = async () => {
    setIsLoading(true);
    try {
      const { postSolutionRequest } = await import("../../api/client");
      const response = await postSolutionRequest(submissionId, sessionId);
      setRequestCount(response.request_count);
      if (response.solution_revealed && response.solution_text) {
        setSolutionText(response.solution_text);
        setDialogOpen(false);
      } else {
        setDialogOpen(false);
      }
    } catch (e) {
      console.error(e);
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
          onClick={() => setDialogOpen(true)}
          style={{
            marginTop: "10px",
            background: "transparent",
            color: "#f38ba8",
            border: "1.5px solid #f38ba8",
            borderRadius: "5px",
            padding: "8px 14px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
            width: "100%",
          }}
        >
          Show Solution
        </button>
      )}

      {dialogOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "#1e1e2e", border: "1px solid #313244", borderRadius: "8px", padding: "24px", maxWidth: "400px", width: "90%" }}>
            <div style={{ color: "#cdd6f4", fontSize: "18px", fontWeight: 700, marginBottom: "12px" }}>
              {dialogContent[requestCount].title}
            </div>
            <div style={{ color: "#a6adc8", fontSize: "14px", marginBottom: "20px" }}>
              {dialogContent[requestCount].body}
            </div>
            <div style={{ display: "flex", gap: "12px" }}>
              <button
                onClick={() => setDialogOpen(false)}
                style={{ flex: 1, background: "#313244", color: "#cdd6f4", border: "none", borderRadius: "5px", padding: "10px", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
              >
                {dialogContent[requestCount].cancel}
              </button>
              <button
                onClick={handleRequest}
                disabled={isLoading}
                style={{ flex: 1, background: "#f38ba8", color: "#1e1e2e", border: "none", borderRadius: "5px", padding: "10px", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
              >
                {dialogContent[requestCount].confirm}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
