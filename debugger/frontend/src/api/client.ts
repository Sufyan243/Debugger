// TODO: Regenerate this file by running: npm run generate:api
// This is a hand-written stub matching the current backend schema.
// Run the generator once the backend is available at http://localhost:8000

export interface ExecuteRequest {
  code: string;
  language: string;
  session_id: string;
  prediction?: string | null;
}

export interface ClassificationData {
  exception_type: string;
  concept_category: string;
  cognitive_skill: string;
}

export interface ContextualHint {
  hint_text: string;
  affected_line: number | null;
  explanation: string;
}

export interface SolutionData {
  solution_code: string;
  explanation: string;
  changes_needed: string[];
}

export interface ExecuteData {
  submission_id: string;
  success: boolean;
  stdout: string;
  stderr: string;
  traceback: string;
  execution_time: number;
  classification: ClassificationData | null;
  reflection_question?: string | null;
  contextual_hint?: ContextualHint | null;
  solution?: SolutionData | null;
  prediction_match?: boolean | null;
  metacognitive_accuracy?: number | null;
}

export interface ExecuteResponse {
  status: string;
  data: ExecuteData | null;
  message: string;
  code?: string;
}

export async function postExecute(req: ExecuteRequest): Promise<ExecuteResponse> {
  const response = await fetch("http://localhost:8000/api/v1/execute", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

export async function postReflect(submissionId: string, responseText: string, sessionId: string) {
  const response = await fetch("http://localhost:8000/api/v1/reflect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ submission_id: submissionId, response_text: responseText, session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function postHint(submissionId: string, tier: number, sessionId: string) {
  const response = await fetch("http://localhost:8000/api/v1/hint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ submission_id: submissionId, tier, session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function postSolutionRequest(submissionId: string, sessionId: string) {
  const response = await fetch("http://localhost:8000/api/v1/solution-request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ submission_id: submissionId, session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}
