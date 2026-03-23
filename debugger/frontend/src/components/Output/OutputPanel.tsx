import { ExecuteData } from "../../api/client";
import { ExecuteError } from "../../hooks/useExecute";
import SkeletonLoader from "./SkeletonLoader";
import SuccessOutput from "./SuccessOutput";
import ClassifiedError from "./ClassifiedError";
import UnclassifiedError from "./UnclassifiedError";

type ExecuteState = "idle" | "executing" | "success" | "classified_error" | "unclassified_error" | "api_error" | "unchanged";

interface OutputPanelProps {
  state: ExecuteState;
  result: ExecuteData | null;
  prediction: string | null;
  submissionId: string | null;
  sessionId: string;
  authToken: string;
  error: ExecuteError | null;
  onSessionExpired?: () => void;
}

const ERROR_MESSAGES: Record<string, { title: string; body: string }> = {
  EXEC_TIMEOUT: {
    title: "Execution timed out",
    body: "Your code took too long to run. Check for infinite loops or long-running operations.",
  },
  EXEC_RESOURCE_LIMIT: {
    title: "Resource limit exceeded",
    body: "Your code used too much memory or CPU. Try reducing data sizes or optimising loops.",
  },
  RATE_LIMITED: {
    title: "Too many requests",
    body: "You've sent too many requests. Wait a moment before running again.",
  },
  EMPTY_CODE: {
    title: "Nothing to run",
    body: "Your code is empty or contains only whitespace. Write some code first.",
  },
};

export default function OutputPanel({
  state, result, prediction, submissionId, sessionId, authToken, error, onSessionExpired,
}: OutputPanelProps) {
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
        reflectionQuestion={result.reflection_question ?? null}
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
        submissionId={submissionId ?? ""}
        sessionId={sessionId}
        authToken={authToken}
        failedAttempts={result.failed_attempts ?? null}
        onSessionExpired={onSessionExpired}
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
    const code = error?.code ?? null;

    // Auth-expired: prompt re-authentication
    if (code === "AUTH_EXPIRED" || code === "TOKEN_REVOKED") {
      return (
        <div style={{ padding: 16 }}>
          <div style={{ color: "#f38ba8", fontWeight: 600, marginBottom: 8 }}>Session expired</div>
          <div style={{ color: "#a6adc8", fontSize: 13, marginBottom: 12 }}>
            Your session has expired. Sign in again to continue.
          </div>
          {onSessionExpired && (
            <button
              onClick={onSessionExpired}
              style={{ background: "#6366f1", color: "#fff", border: "none", borderRadius: 6, padding: "7px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              Sign in
            </button>
          )}
        </div>
      );
    }

    const known = code ? ERROR_MESSAGES[code] : null;
    if (known) {
      return (
        <div style={{ padding: 16 }}>
          <div style={{ color: "#f38ba8", fontWeight: 600, marginBottom: 6 }}>{known.title}</div>
          <div style={{ color: "#a6adc8", fontSize: 13 }}>{known.body}</div>
        </div>
      );
    }

    return (
      <div style={{ color: "#f38ba8", padding: 16, fontSize: 13 }}>
        {error?.message ?? "An error occurred. Please try again."}
      </div>
    );
  }

  return null;
}
