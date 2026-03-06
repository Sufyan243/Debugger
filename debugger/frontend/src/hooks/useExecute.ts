import { useState } from "react";
import { postExecute, ExecuteData } from "../api/client";

type ExecuteState = "idle" | "executing" | "success" | "classified_error" | "unclassified_error" | "api_error";

export function useExecute() {
  const [state, setState] = useState<ExecuteState>("idle");
  const [result, setResult] = useState<ExecuteData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSubmittedCode, setLastSubmittedCode] = useState<string | null>(null);
  const [sameCode, setSameCode] = useState(false);

  const isExecuting = state === "executing";

  const runCode = async (code: string, sessionId: string, prediction?: string | null): Promise<void> => {
    if (code === lastSubmittedCode) {
      setSameCode(true);
      return;
    }

    setState("executing");
    setResult(null);
    setError(null);
    setSameCode(false);

    try {
      const response = await postExecute({
        code,
        language: "python",
        session_id: sessionId,
        prediction,
      });

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
        setError(response.message);
      }
    } catch (e: any) {
      setState("api_error");
      setError(e.message);
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
    runCode,
    resetToIdle,
  };
}
