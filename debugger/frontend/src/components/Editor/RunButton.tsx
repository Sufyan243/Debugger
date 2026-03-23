interface RunButtonProps {
  onClick: () => void;
  disabled: boolean;
  sessionUnavailable?: boolean;
}

export default function RunButton({ onClick, disabled, sessionUnavailable }: RunButtonProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
      <button
        onClick={onClick}
        disabled={disabled}
        className="bg-[#a6e3a1] text-[#1e1e2e] font-bold px-4 py-2 rounded disabled:opacity-50 disabled:cursor-not-allowed"
      >
        ▶ Run Code
      </button>
      {sessionUnavailable && (
        <span style={{ fontSize: 11, color: "#f38ba8" }}>
          Session unavailable — please refresh the page.
        </span>
      )}
    </div>
  );
}
