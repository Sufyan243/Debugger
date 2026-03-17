import { ExecuteData } from "../../api/client";
import SkeletonLoader from "./SkeletonLoader";
import SuccessOutput from "./SuccessOutput";
import ClassifiedError from "./ClassifiedError";
import UnclassifiedError from "./UnclassifiedError";

type ExecuteState = "idle" | "executing" | "success" | "classified_error" | "unclassified_error" | "api_error";

interface OutputPanelProps {
  state: ExecuteState;
  result: ExecuteData | null;
  prediction: string | null;
  submissionId: string | null;
  sessionId: string;
}

export default function OutputPanel({ state, result, prediction, submissionId, sessionId }: OutputPanelProps) {
  if (state === "idle") {
    return (
      <p className="text-[#585b70] text-sm text-center mt-16">
        Run your code to see output here.
      </p>
    );
  }

  if (state === "executing") {
    return <SkeletonLoader />;
  }

  if (state === "success" && result) {
    return (
      <SuccessOutput
        stdout={result.stdout}
        executionTime={result.execution_time}
        prediction={prediction}
        predictionMatch={result.prediction_match ?? null}
        metacognitiveAccuracy={result.metacognitive_accuracy ?? null}
      />
    );
  }

  if (state === "classified_error" && result && result.classification) {
    return (
      <ClassifiedError
        classification={result.classification}
        traceback={result.traceback}
        executionTime={result.execution_time}
        prediction={prediction}
        reflectionQuestion={result.reflection_question ?? undefined}
        contextualHint={result.contextual_hint ?? undefined}
        solution={result.solution ?? undefined}
        submissionId={submissionId ?? ""}
        sessionId={sessionId}
      />
    );
  }

  if (state === "unclassified_error" && result) {
    return (
      <UnclassifiedError
        traceback={result.traceback}
        stderr={result.stderr}
        executionTime={result.execution_time}
        prediction={prediction}
        predictionMatch={result.prediction_match ?? null}
        metacognitiveAccuracy={result.metacognitive_accuracy ?? null}
      />
    );
  }

  if (state === "api_error") {
    return (
      <div style={{ color: "#f38ba8", padding: "16px" }}>
        An error occurred. Please try again.
      </div>
    );
  }

  return null;
}
