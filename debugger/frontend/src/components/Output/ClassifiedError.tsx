import { useState } from "react";
import { ClassificationData, postHint } from "../../api/client";
import HintTiers from "./HintTiers";
import ReflectionGate from "./ReflectionGate";
import SolutionGate from "./SolutionGate";

interface ContextualHint {
  hint_text: string;
  affected_line: number | null;
  explanation: string;
}

interface ClassifiedErrorProps {
  classification: ClassificationData;
  traceback: string;
  executionTime: number;
  prediction: string | null;
  reflectionQuestion?: string;
  contextualHint?: ContextualHint;
  submissionId: string;
  sessionId: string;
  authToken: string;
  failedAttempts?: number | null;
}

export default function ClassifiedError({
  classification,
  traceback,
  executionTime,
  prediction,
  reflectionQuestion,
  contextualHint,
  submissionId,
  sessionId,
  authToken,
  failedAttempts,
}: ClassifiedErrorProps) {
  const [expanded, setExpanded] = useState(false);
  const [hintUnlocked, setHintUnlocked] = useState(false);

  const initialTier = !failedAttempts || failedAttempts <= 2 ? 1 : failedAttempts <= 4 ? 2 : 3;
  const [hints, setHints] = useState<Array<{ tier: number; tier_name: string; hint_text: string }>>(
    contextualHint
      ? [{ tier: initialTier, tier_name: `Tier ${initialTier}`, hint_text: contextualHint.hint_text }]
      : []
  );
  const [unlockedTiers, setUnlockedTiers] = useState<Set<number>>(new Set(contextualHint ? [initialTier] : []));

  async function handleUnlockNext(tier: number) {
    try {
      const data = await postHint(submissionId, tier, sessionId, authToken);
      setHints(prev => {
        if (prev.some(h => h.tier === tier)) return prev;
        return [...prev, { tier: data.tier, tier_name: data.tier_name, hint_text: data.hint_text }]
          .sort((a, b) => a.tier - b.tier);
      });
      setUnlockedTiers(prev => new Set([...prev, tier]));
    } catch {
      // silently ignore — hint unavailable
    }
  }

  return (
    <div>
      <div style={{ background: "#2d1b3d", border: "1px solid #cba6f7", borderRadius: "8px", padding: "16px", marginBottom: "16px" }}>
        <div style={{ color: "#cba6f7", fontSize: "11px", textTransform: "uppercase", marginBottom: "8px" }}>
          {classification.exception_type} · {classification.concept_category}
        </div>
        <div style={{ color: "#f5c2e7", fontSize: "20px", fontWeight: "bold", marginBottom: "8px" }}>
          {classification.concept_category}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ color: "#a6adc8", fontSize: "12px" }}>Skill gap: {classification.cognitive_skill}</div>
          <div style={{ color: "#585b70", fontSize: "11px" }}>Failed in {executionTime.toFixed(2)}s</div>
        </div>
      </div>

      {reflectionQuestion && !hintUnlocked && (
        <ReflectionGate
          submissionId={submissionId}
          sessionId={sessionId}
          question={reflectionQuestion}
          onUnlocked={() => setHintUnlocked(true)}
        />
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        style={{ color: "#a6adc8", background: "none", border: "none", cursor: "pointer", fontSize: "14px", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}
      >
        <span style={{ fontSize: "10px" }}>{expanded ? "\u25BE" : "\u25B8"}</span>
        {expanded ? "Hide" : "Show"} raw traceback
      </button>

      {expanded && (
        <div style={{ background: "#11111b", border: "1px solid #313244", borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
          <pre style={{ fontFamily: "monospace", color: "#f38ba8", whiteSpace: "pre-wrap", margin: 0, fontSize: "13px" }}>
            {traceback}
          </pre>
        </div>
      )}

      {(hintUnlocked || !reflectionQuestion) && hints.length > 0 && (
        <HintTiers
          hints={hints}
          unlockedTiers={unlockedTiers}
          onUnlockNext={handleUnlockNext}
        />
      )}

      {(hintUnlocked || !reflectionQuestion) && (
        <SolutionGate
          submissionId={submissionId}
          sessionId={sessionId}
          authToken={authToken}
          isVisible={unlockedTiers.has(3)}
        />
      )}

      {prediction && prediction.trim() && (
        <div style={{ borderLeft: "3px solid #585b70", padding: "6px 10px", marginTop: "14px", color: "#a6adc8", fontSize: "12px", fontStyle: "italic" }}>
          Your prediction: "{prediction}"
        </div>
      )}
    </div>
  );
}
