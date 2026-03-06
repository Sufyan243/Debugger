interface SuccessOutputProps {
  stdout: string;
  executionTime: number;
  prediction: string | null;
}

export default function SuccessOutput({ stdout, executionTime, prediction }: SuccessOutputProps) {
  return (
    <div style={{ border: "1px solid #a6e3a1", background: "#1e3a2e", padding: "16px", borderRadius: "8px" }}>
      <div style={{ color: "#a6e3a1", fontSize: "12px", textTransform: "uppercase", marginBottom: "8px" }}>
        ✓ Executed in {executionTime.toFixed(2)}s
      </div>
      <pre style={{ fontFamily: "monospace", color: "#cdd6f4", whiteSpace: "pre-wrap", margin: 0 }}>
        {stdout}
      </pre>
      {prediction && prediction.trim() && (
        <div style={{ borderLeft: "3px solid #585b70", padding: "6px 10px", marginTop: "14px", color: "#a6adc8", fontSize: "12px", fontStyle: "italic" }}>
          Your prediction: "{prediction}"
        </div>
      )}
    </div>
  );
}
