interface UnclassifiedErrorProps {
  traceback: string;
  prediction: string | null;
}

export default function UnclassifiedError({ traceback, prediction }: UnclassifiedErrorProps) {
  return (
    <div>
      <div style={{ background: "#11111b", border: "1px solid #f38ba8", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
        <pre style={{ fontFamily: "monospace", color: "#f38ba8", whiteSpace: "pre-wrap", margin: 0, fontSize: "13px" }}>
          {traceback}
        </pre>
      </div>
      <p style={{ color: "#a6adc8", fontSize: "13px", fontStyle: "italic" }}>
        This error type isn't in our system yet. Read the traceback carefully.
      </p>
      {prediction && prediction.trim() && (
        <div style={{ borderLeft: "3px solid #585b70", padding: "6px 10px", marginTop: "14px", color: "#a6adc8", fontSize: "12px", fontStyle: "italic" }}>
          Your prediction: "{prediction}"
        </div>
      )}
    </div>
  );
}
