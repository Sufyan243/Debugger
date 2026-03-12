import { useState } from "react";

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

interface HelpPanelProps {
  contextualHint: ContextualHint | null;
  solution: SolutionData | null;
}

export default function HelpPanel({ contextualHint, solution }: HelpPanelProps) {
  const [showSolution, setShowSolution] = useState(false);

  if (!contextualHint && !solution) {
    return null;
  }

  return (
    <div style={{ marginBottom: "16px" }}>
      {/* Contextual Hint */}
      {contextualHint && (
        <div
          style={{
            borderRadius: "7px",
            border: "1px solid #313244",
            padding: "13px 15px",
            marginBottom: "10px",
            background: "#1e1e2e",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <span
              style={{
                fontSize: "10px",
                fontWeight: 700,
                borderRadius: "3px",
                padding: "2px 7px",
                textTransform: "uppercase",
                background: "#1e3a2e",
                color: "#a6e3a1",
              }}
            >
              💡 Hint
            </span>
            {contextualHint.affected_line && (
              <span style={{ fontSize: "11px", color: "#f9e2af" }}>
                Line {contextualHint.affected_line}
              </span>
            )}
          </div>
          <div style={{ fontSize: "13px", color: "#cdd6f4", lineHeight: 1.6, marginBottom: "8px" }}>
            {contextualHint.hint_text}
          </div>
          <div
            style={{
              fontSize: "12px",
              color: "#a6adc8",
              lineHeight: 1.5,
              padding: "8px 10px",
              background: "#181825",
              borderRadius: "5px",
              borderLeft: "3px solid #89b4fa",
            }}
          >
            {contextualHint.explanation}
          </div>
        </div>
      )}

      {/* Solution Section */}
      {solution && (
        <div
          style={{
            borderRadius: "7px",
            border: "1px solid #313244",
            padding: "13px 15px",
            background: "#1e1e2e",
          }}
        >
          {!showSolution ? (
            <button
              onClick={() => setShowSolution(true)}
              style={{
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
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    borderRadius: "3px",
                    padding: "2px 7px",
                    textTransform: "uppercase",
                    background: "#3e2a2e",
                    color: "#f38ba8",
                  }}
                >
                  ✓ Solution
                </span>
              </div>

              {/* Changes Needed */}
              <div style={{ marginBottom: "12px" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "#a6adc8", marginBottom: "6px" }}>
                  Changes needed:
                </div>
                {solution.changes_needed.map((change, idx) => (
                  <div
                    key={idx}
                    style={{
                      fontSize: "12px",
                      color: "#cdd6f4",
                      padding: "4px 0",
                      paddingLeft: "12px",
                      position: "relative",
                    }}
                  >
                    <span style={{ position: "absolute", left: "0", color: "#f38ba8" }}>•</span>
                    {change}
                  </div>
                ))}
              </div>

              {/* Explanation */}
              <div
                style={{
                  fontSize: "12px",
                  color: "#a6adc8",
                  lineHeight: 1.5,
                  padding: "8px 10px",
                  background: "#181825",
                  borderRadius: "5px",
                  marginBottom: "12px",
                }}
              >
                {solution.explanation}
              </div>

              {/* Solution Code */}
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#a6adc8", marginBottom: "6px" }}>
                Working code:
              </div>
              <pre
                style={{
                  background: "#181825",
                  padding: "10px",
                  borderRadius: "5px",
                  fontSize: "12px",
                  color: "#cdd6f4",
                  overflowX: "auto",
                  margin: 0,
                  fontFamily: "monospace",
                  lineHeight: 1.5,
                }}
              >
                {solution.solution_code}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}
