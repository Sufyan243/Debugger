interface SuccessOutputProps {
  stdout: string;
  executionTime: number;
  prediction: string | null;
  predictionMatch: boolean | null;
  metacognitiveAccuracy: number | null;
}

export default function SuccessOutput({ stdout, executionTime, prediction, predictionMatch, metacognitiveAccuracy }: SuccessOutputProps) {
  return (
    <div style={{ border: "1px solid #a6e3a1", background: "#1e3a2e", padding: "16px", borderRadius: "8px" }}>
      <div style={{ color: "#a6e3a1", fontSize: "12px", textTransform: "uppercase", marginBottom: "8px" }}>
        ✓ Executed in {executionTime.toFixed(2)}s
      </div>
      <pre style={{ fontFamily: "monospace", color: "#cdd6f4", whiteSpace: "pre-wrap", margin: 0 }}>
        {stdout}
      </pre>
      {prediction !== null && prediction.trim() !== '' && predictionMatch !== null && (
        <div style={{ marginTop: "16px", padding: "12px", background: "#181825", borderRadius: "6px", border: "1px solid #313244" }}>
          <div style={{ color: "#a6adc8", fontSize: "13px", fontWeight: "600", marginBottom: "12px" }}>Your Prediction vs Actual Output</div>
          <div style={{ marginBottom: "12px" }}>
            <div style={{ color: "#a6adc8", fontSize: "11px", textTransform: "uppercase", marginBottom: "4px" }}>Your Prediction</div>
            <div style={{ color: "#cdd6f4", fontSize: "13px", fontFamily: "monospace" }}>{prediction}</div>
          </div>
          <div style={{ marginBottom: "12px" }}>
            <div style={{ color: "#a6adc8", fontSize: "11px", textTransform: "uppercase", marginBottom: "4px" }}>Actual Output</div>
            <div style={{ color: "#cdd6f4", fontSize: "13px", fontFamily: "monospace" }}>{stdout}</div>
          </div>
          {predictionMatch ? (
            <div style={{ color: "#a6e3a1", fontSize: "13px", fontWeight: "500" }}>✓ Correct prediction!</div>
          ) : (
            <div>
              <div style={{ color: "#f38ba8", fontSize: "13px", fontWeight: "500", marginBottom: "6px" }}>✗ Mismatch detected</div>
              <div style={{ color: "#a6adc8", fontSize: "12px", fontStyle: "italic" }}>What assumption was incorrect?</div>
            </div>
          )}
          {metacognitiveAccuracy !== null && (
            <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid #313244", color: "#a6adc8", fontSize: "12px" }}>
              Session accuracy: {(metacognitiveAccuracy * 100).toFixed(0)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}
