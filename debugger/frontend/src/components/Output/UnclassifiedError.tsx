interface UnclassifiedErrorProps {
  traceback: string;
  stderr: string;
  executionTime: number;
  prediction: string | null;
  predictionMatch: boolean | null;
  metacognitiveAccuracy: number | null;
}

export default function UnclassifiedError({ traceback, stderr, executionTime, prediction, predictionMatch, metacognitiveAccuracy }: UnclassifiedErrorProps) {
  const actualOutput = traceback || stderr;
  return (
    <div>
      <div style={{ background: "#11111b", border: "1px solid #f38ba8", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
        <div style={{ color: "#585b70", fontSize: "11px", textAlign: "right", marginBottom: "6px" }}>Failed in {executionTime.toFixed(2)}s</div>
        <pre style={{ fontFamily: "monospace", color: "#f38ba8", whiteSpace: "pre-wrap", margin: 0, fontSize: "13px" }}>
          {traceback}
        </pre>
      </div>
      <p style={{ color: "#a6adc8", fontSize: "13px", fontStyle: "italic" }}>
        This error type isn't in our system yet. Read the traceback carefully.
      </p>
      {prediction !== null && prediction.trim() !== '' && predictionMatch !== null && (
        <div style={{ marginTop: "16px", padding: "12px", background: "#181825", borderRadius: "6px", border: "1px solid #313244" }}>
          <div style={{ color: "#a6adc8", fontSize: "13px", fontWeight: "600", marginBottom: "12px" }}>Your Prediction vs Actual Output</div>
          <div style={{ marginBottom: "12px" }}>
            <div style={{ color: "#a6adc8", fontSize: "11px", textTransform: "uppercase", marginBottom: "4px" }}>Your Prediction</div>
            <div style={{ color: "#cdd6f4", fontSize: "13px", fontFamily: "monospace" }}>{prediction}</div>
          </div>
          <div style={{ marginBottom: "12px" }}>
            <div style={{ color: "#a6adc8", fontSize: "11px", textTransform: "uppercase", marginBottom: "4px" }}>Actual Output</div>
            <div style={{ color: "#f38ba8", fontSize: "13px", fontFamily: "monospace" }}>{actualOutput}</div>
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
