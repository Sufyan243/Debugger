interface ContextualHint {
  hint_text: string;
  affected_line: number | null;
  explanation: string;
}

interface HelpPanelProps {
  contextualHint: ContextualHint | null;
}

export default function HelpPanel({ contextualHint }: HelpPanelProps) {
  if (!contextualHint) return null;

  return (
    <div style={{ marginBottom: "16px" }}>
      <div
        style={{
          borderRadius: "7px",
          border: "1px solid #313244",
          padding: "13px 15px",
          background: "#1e1e2e",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <span
            style={{
              fontSize: "10px", fontWeight: 700, borderRadius: "3px", padding: "2px 7px",
              textTransform: "uppercase", background: "#1e3a2e", color: "#a6e3a1",
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
            fontSize: "12px", color: "#a6adc8", lineHeight: 1.5,
            padding: "8px 10px", background: "#181825", borderRadius: "5px",
            borderLeft: "3px solid #89b4fa",
          }}
        >
          {contextualHint.explanation}
        </div>
      </div>
    </div>
  );
}
