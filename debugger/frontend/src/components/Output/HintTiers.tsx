interface HintData {
  tier: number;
  tier_name: string;
  hint_text: string;
}

interface HintTiersProps {
  hints: HintData[];
  unlockedTiers: Set<number>;
  onUnlockNext: (tier: number) => void;
}

export default function HintTiers({ hints, unlockedTiers, onUnlockNext }: HintTiersProps) {
  return (
    <div style={{ marginBottom: "16px" }}>
      <div style={{ fontSize: "12px", fontWeight: 700, color: "#a6adc8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
        Hints
      </div>
      {hints.map((hint) => {
        const isUnlocked = unlockedTiers.has(hint.tier);
        const canUnlockNext = hint.tier < 3 && isUnlocked && !unlockedTiers.has(hint.tier + 1);

        return (
          <div
            key={hint.tier}
            style={{
              borderRadius: "7px",
              border: "1px solid #313244",
              padding: "11px 13px",
              marginBottom: "8px",
              background: isUnlocked ? "#1e1e2e" : "#181825",
              opacity: isUnlocked ? 1 : 0.6,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
              <span
                style={{
                  fontSize: "10px", fontWeight: 700, borderRadius: "3px", padding: "2px 7px",
                  textTransform: "uppercase",
                  background: isUnlocked ? "#1e3a2e" : "#313244",
                  color: isUnlocked ? "#a6e3a1" : "#585b70",
                }}
              >
                Hint {hint.tier}
              </span>
              <span style={{ fontSize: "12px", fontWeight: 600, color: isUnlocked ? "#cdd6f4" : "#45475a" }}>
                {hint.tier_name}
              </span>
              <span style={{ marginLeft: "auto", fontSize: "11px", color: isUnlocked ? "#a6e3a1" : "#585b70" }}>
                {isUnlocked ? "✓ Unlocked" : "🔒"}
              </span>
            </div>
            <div
              style={{
                fontSize: "13px",
                color: isUnlocked ? "#cdd6f4" : "#45475a",
                lineHeight: 1.5,
                fontStyle: isUnlocked ? "normal" : "italic",
              }}
            >
              {isUnlocked ? hint.hint_text : `Unlock Hint ${hint.tier === 1 ? "1" : hint.tier - 1} first to reveal this.`}
            </div>
            {canUnlockNext && (
              <button
                onClick={() => onUnlockNext(hint.tier + 1)}
                style={{
                  marginTop: "8px", background: "#3b82f6", color: "#fff", border: "none",
                  borderRadius: "5px", padding: "6px 14px", fontSize: "12px", fontWeight: 600,
                  cursor: "pointer", width: "100%",
                }}
              >
                Get next hint →
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
