import { useState } from "react";
import { postReflect } from "../../api/client";

interface ReflectionGateProps {
  submissionId: string;
  sessionId: string;
  question: string;
  authToken: string;
  onUnlocked: () => void;
}

export default function ReflectionGate({ submissionId, sessionId, question, authToken, onUnlocked }: ReflectionGateProps) {
  const [text, setText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    const trimmed = text.trim();
    if (trimmed.length < 10) {
      setError("Please write at least 10 characters before submitting.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await postReflect(submissionId, trimmed, sessionId, authToken);
      setSubmitted(true);
      onUnlocked();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ marginBottom: "16px" }}>
      <div style={{ fontSize: "12px", fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
        Reflection
      </div>
      <div style={{ fontSize: "14px", fontWeight: 600, color: "#cdd6f4", marginBottom: "8px" }}>
        {question}
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={submitted}
        placeholder="Type your thoughts here… (min 10 characters)"
        maxLength={2000}
        style={{ width: "100%", background: "#1e1e2e", border: `1px solid ${error ? "#f38ba8" : "#45475a"}`, color: "#cdd6f4", borderRadius: "6px", padding: "8px 10px", fontSize: "13px", resize: "vertical", minHeight: "60px", marginBottom: "8px" }}
      />
      {error && (
        <div style={{ color: "#f38ba8", fontSize: "12px", marginBottom: "8px" }}>
          ✗ {error}
        </div>
      )}
      {!submitted ? (
        <button
          onClick={handleSubmit}
          disabled={text.trim().length < 10 || isSubmitting}
          style={{ background: "#cba6f7", color: "#1e1e2e", border: "none", borderRadius: "5px", padding: "7px 16px", fontWeight: 700, fontSize: "13px", cursor: "pointer" }}
          className="disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? "Submitting…" : "Submit Reflection"}
        </button>
      ) : (
        <div style={{ color: "#a6e3a1", fontSize: "12px", marginTop: "6px" }}>
          ✓ Reflection submitted — Hint 1 unlocked
        </div>
      )}
    </div>
  );
}
