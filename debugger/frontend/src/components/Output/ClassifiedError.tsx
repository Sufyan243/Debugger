import { useState } from "react";
import { ClassificationData } from "../../api/client";
import HelpPanel from "./HelpPanel";

interface ContextualHint {
  hint_text: string;
  affected_line: number | null;
  explanation: string;
}

interface SolutionData {
  solution_code: string;
  explanation: string;
  changes_needed: string[];
}

interface ClassifiedErrorProps {
  classification: ClassificationData;
  traceback: string;
  prediction: string | null;
  reflectionQuestion?: string;
  contextualHint?: ContextualHint;
  solution?: SolutionData;
  submissionId: string;
  sessionId: string;
}

export default function ClassifiedError({
  classification,
  traceback,
  prediction,
  reflectionQuestion,
  contextualHint,
  solution,
  submissionId,
  sessionId,
}: ClassifiedErrorProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <div style={{ background: "#2d1b3d", border: "1px solid #cba6f7", borderRadius: "8px", padding: "16px", marginBottom: "16px" }}>
        <div style={{ color: "#cba6f7", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>
          {classification.exception_type} · {classification.concept_category}
        </div>
        <div style={{ color: "#f5c2e7", fontSize: "20px", fontWeight: "bold", marginBottom: "8px" }}>
          {classification.concept_category}
        </div>
        <div style={{ color: "#a6adc8", fontSize: "12px" }}>
          Skill gap: {classification.cognitive_skill}
        </div>
      </div>

      {reflectionQuestion && (
        <div
          style={{
            background: "#1e1e2e",
            border: "1px solid #313244",
            borderRadius: "7px",
            padding: "13px 15px",
            marginBottom: "12px",
          }}
        >
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#a6adc8", marginBottom: "6px" }}>
            💭 Reflection Question
          </div>
          <div style={{ fontSize: "13px", color: "#cdd6f4", lineHeight: 1.5 }}>
            {reflectionQuestion}
          </div>
        </div>
      )}
      
      <button
        onClick={() => setExpanded(!expanded)}
        style={{ color: "#a6adc8", background: "none", border: "none", cursor: "pointer", fontSize: "14px", marginBottom: "8px" }}
      >
        {expanded ? "▼" : "▶"} {expanded ? "Hide" : "Show"} raw traceback
      </button>
      
      {expanded && (
        <div style={{ background: "#11111b", border: "1px solid #313244", borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
          <pre style={{ fontFamily: "monospace", color: "#f38ba8", whiteSpace: "pre-wrap", margin: 0, fontSize: "13px" }}>
            {traceback}
          </pre>
        </div>
      )}

      {(contextualHint || solution) && (
        <HelpPanel contextualHint={contextualHint || null} solution={solution || null} />
      )}
      
      {prediction && prediction.trim() && (
        <div style={{ borderLeft: "3px solid #585b70", padding: "6px 10px", marginTop: "14px", color: "#a6adc8", fontSize: "12px", fontStyle: "italic" }}>
          Your prediction: "{prediction}"
        </div>
      )}
    </div>
  );
}
