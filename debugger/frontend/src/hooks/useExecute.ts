import { useState } from "react";
import { postExecute, ExecuteData } from "../api/client";

type ExecuteState = "idle" | "executing" | "success" | "classified_error" | "unclassified_error" | "api_error" | "unchanged";

export interface ExecuteError {
  message: string;
  code: string | null;
}

export function useExecute() {
  const [state, setState] = useState<ExecuteState>("idle");
  const [result, setResult] = useState<ExecuteData | null>(null);
  const [error, setError] = useState<ExecuteError | null>(null);
  const [lastSubmittedCode, setLastSubmittedCode] = useState<string | null>(null);
  const [sameCode, setSameCode] = useState(false);
  const [submittedPrediction, setSubmittedPrediction] = useState<string | null>(null);

  const isExecuting = state === "executing";

  const runCode = async (code: string, sessionId: string, authToken: string, prediction?: string | null): Promise<void> => {
    // Client-side whitespace-only guard
    if (!code.trim()) {
      setError({ message: "Code must not be empty or whitespace only.", code: "EMPTY_CODE" });
      setState("api_error");
      return;
    }

    // Client-side fast-path: skip the round-trip if we already know it's unchanged.
    if (code === lastSubmittedCode) {
      setSameCode(true);
      setState("unchanged");
      return;
    }

    setState("executing");
    setResult(null);
    setError(null);
    setSameCode(false);
    setSubmittedPrediction(prediction ?? null);

    try {
      const response = await postExecute(
        { code, language: "python", session_id: sessionId, prediction },
        authToken,
      );

      // Server-side unchanged-code gate: the server may reject the submission
      // even if the client thinks it's new (e.g. after a page refresh).
      if (response.code === "UNCHANGED_CODE") {
        setSameCode(true);
        setState("unchanged");
        setError({ message: response.message, code: "UNCHANGED_CODE" });
        return;
      }

      setLastSubmittedCode(code);

      if (response.data) {
        if (response.data.success) {
          setState("success");
          setResult(response.data);
        } else if (response.data.classification !== null) {
          setState("classified_error");
          setResult(response.data);
        } else {
          setState("unclassified_error");
          setResult(response.data);
        }
      } else {
        setState("api_error");
        setError({ message: response.message, code: response.code ?? null });
      }
    } catch (e: any) {
      setState("api_error");
      // Map HTTP status codes to stable error codes the UI can branch on.
      const status: number | undefined = e?.status;
      let code: string | null = e?.code ?? null;
      if (!code) {
        if (status === 401 || status === 403) code = "AUTH_EXPIRED";
        else if (status === 429) code = "RATE_LIMITED";
      }
      setError({ message: e?.message ?? "Request failed", code });
    }
  };

  const resetToIdle = () => {
    setState("idle");
    setResult(null);
    setError(null);
    setSameCode(false);
  };

  return {
    state,
    isExecuting,
    result,
    error,
    sameCode,
    submittedPrediction,
    runCode,
    resetToIdle,
  };
}
