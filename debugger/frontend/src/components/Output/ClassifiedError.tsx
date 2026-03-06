import { useState, useEffect } from "react";
import { ClassificationData } from "../../api/client";
import ReflectionGate from "./ReflectionGate";
import HintTiers from "./HintTiers";
import SolutionGate from "./SolutionGate";

interface ClassifiedErrorProps {
  classification: ClassificationData;
  traceback: string;
  prediction: string | null;
  reflectionQuestion?: string;
  hints?: Array<{ tier: number; tier_name: string; hint_text: string; unlocked: boolean }>;
  hintAutoUnlocked?: boolean;
  submissionId: string;
  sessionId: string;
}

export default function ClassifiedError({
  classification,
  traceback,
  prediction,
  reflectionQuestion,
  hints,
  hintAutoUnlocked,
  submissionId,
  sessionId,
}: ClassifiedErrorProps) {
  const [expanded, setExpanded] = useState(false);
  const [unlockedTiers, setUnlockedTiers] = useState<Set<number>>(new Set());
  const [showSolutionGate, setShowSolutionGate] = useState(false);

  useEffect(() => {
    if (hintAutoUnlocked) {
      setUnlockedTiers(new Set([1]));
    }
  }, [hintAutoUnlocked]);

  const handleReflectionUnlock = () => {
    setUnlockedTiers(new Set([1]));
  };

  const handleUnlockNext = (tier: number) => {
    setUnlockedTiers((prev) => new Set([...prev, tier]));
  };

  const handleShowSolution = () => {
    setShowSolutionGate(true);
  };

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

      {reflectionQuestion && hints && !unlockedTiers.has(1) && (
        <ReflectionGate
          submissionId={submissionId}
          sessionId={sessionId}
          question={reflectionQuestion}
          onUnlocked={handleReflectionUnlock}
        />
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

      {hints && hints.length > 0 && (
        <HintTiers
          hints={hints}
          unlockedTiers={unlockedTiers}
          onUnlockNext={handleUnlockNext}
          onShowSolution={handleShowSolution}
        />
      )}

      {unlockedTiers.has(3) && (
        <SolutionGate submissionId={submissionId} sessionId={sessionId} isVisible={showSolutionGate} />
      )}
      
      {prediction && prediction.trim() && (
        <div style={{ borderLeft: "3px solid #585b70", padding: "6px 10px", marginTop: "14px", color: "#a6adc8", fontSize: "12px", fontStyle: "italic" }}>
          Your prediction: "{prediction}"
        </div>
      )}
    </div>
  );
}
