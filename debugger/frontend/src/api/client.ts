const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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
  const response = await fetch(`${API_BASE}/api/v1/execute`, {
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
  const response = await fetch(`${API_BASE}/api/v1/reflect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ submission_id: submissionId, response_text: responseText, session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function postHint(submissionId: string, tier: number, sessionId: string) {
  const response = await fetch(`${API_BASE}/api/v1/hint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ submission_id: submissionId, tier, session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function postSolutionRequest(submissionId: string, sessionId: string) {
  const response = await fetch(`${API_BASE}/api/v1/solution-request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ submission_id: submissionId, session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export interface ConceptStatItem {
  concept: string;
  error_count: number;
  attempts: number;
  success_streak: number;
}

export interface ConceptStatsResponse {
  concepts: ConceptStatItem[];
}

export interface WeaknessProfileResponse {
  weak_concepts: ConceptStatItem[];
}

export interface SessionSummaryResponse {
  submissions_count: number;
  errors_count: number;
  concepts_learned: number;
  hints_used: number;
  prediction_accuracy: number;
}

export interface MetacognitiveResponse {
  session_id: string;
  accuracy_score: number;
  total_predictions: number;
  correct_predictions: number;
}

/** Shared fetch utility that injects Authorization: Bearer for all session-scoped requests. */
function sessionFetch(url: string, ownerToken: string, init: RequestInit = {}): Promise<Response> {
  if (!ownerToken) return Promise.reject(new Error("No auth token"));
  return fetch(url, {
    ...init,
    headers: {
      ...(init.headers as Record<string, string> | undefined),
      "Authorization": `Bearer ${ownerToken}`,
    },
  });
}

export interface SessionRegisterResponse {
  session_id: string;
  owner_token: string;
}

export async function registerSession(sessionId: string): Promise<SessionRegisterResponse> {
  const response = await fetch(`${API_BASE}/api/v1/session/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (response.status === 409) throw new Error("SESSION_CONFLICT");
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function recoverSession(sessionId: string, currentToken: string): Promise<SessionRegisterResponse> {
  const response = await fetch(`${API_BASE}/api/v1/session/recover`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Session-Token": currentToken },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function fetchConceptStats(sessionId: string, ownerToken: string): Promise<ConceptStatsResponse> {
  const response = await sessionFetch(`${API_BASE}/api/v1/analytics/concepts?session_id=${sessionId}`, ownerToken);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function fetchWeaknessProfile(sessionId: string, ownerToken: string): Promise<WeaknessProfileResponse> {
  const response = await sessionFetch(`${API_BASE}/api/v1/analytics/weakness?session_id=${sessionId}`, ownerToken);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function fetchSessionSummary(sessionId: string, ownerToken: string): Promise<SessionSummaryResponse> {
  const response = await sessionFetch(`${API_BASE}/api/v1/analytics/session-summary?session_id=${sessionId}`, ownerToken);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function fetchMetacognitive(sessionId: string, ownerToken: string): Promise<MetacognitiveResponse> {
  const response = await sessionFetch(`${API_BASE}/api/v1/analytics/metacognitive?session_id=${sessionId}`, ownerToken);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}
