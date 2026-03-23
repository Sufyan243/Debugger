function validateApiBase(url: string): string {
  if (!url || url.trim() === "" || /REPLACE_WITH_BACKEND_URL/i.test(url)) {
    throw new Error(
      "VITE_API_BASE_URL is missing or set to a placeholder. Check .env.production and CI secrets."
    );
  }
  try {
    new URL(url);
  } catch {
    throw new Error(`VITE_API_BASE_URL is not a valid URL: ${url}`);
  }
  return url;
}

export const API_BASE = validateApiBase(import.meta.env.VITE_API_BASE_URL ?? "");

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
  prediction_match?: boolean | null;
  metacognitive_accuracy?: number | null;
  failed_attempts?: number | null;
}

export interface ExecuteResponse {
  status: string;
  data: ExecuteData | null;
  message: string;
  code?: string;
}

export interface MeResponse {
  sub: string;
  anon: boolean;
  email: string | null;
  avatar_url: string | null;
}

/** Rehydrate session identity from the httpOnly cookie.
 * Returns the user on success.
 * Returns null on 401/403 (explicitly unauthenticated).
 * Throws on 5xx or network errors (transient — caller must not downgrade session). */
export async function fetchMe(): Promise<MeResponse | null> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, { credentials: "include" });
  if (res.status === 401 || res.status === 403) return null;
  if (!res.ok) throw new Error(`fetchMe: transient failure ${res.status}`);
  return await res.json();
}

export async function postExecute(req: ExecuteRequest, _authToken: string): Promise<ExecuteResponse> {
  const response = await fetch(`${API_BASE}/api/v1/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    // Parse the error body so callers get structured status/detail/code.
    let detail = `HTTP ${response.status}`;
    let code: string | undefined;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      if (typeof body.code === "string") code = body.code;
    } catch {}
    // Attach status and code so useExecute can map them to stable error codes.
    const err = new Error(detail) as Error & { status: number; code?: string };
    err.status = response.status;
    err.code = code;
    throw err;
  }

  return await response.json();
}

export async function postReflect(submissionId: string, responseText: string, sessionId: string, _authToken: string) {
  const response = await fetch(`${API_BASE}/api/v1/reflect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ submission_id: submissionId, response_text: responseText, session_id: sessionId }),
  });
  if (!response.ok) {
    let detail = `HTTP error! status: ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch {}
    throw new Error(detail);
  }
  return await response.json();
}

export async function postHint(submissionId: string, tier: number, sessionId: string, _authToken: string) {
  const response = await fetch(`${API_BASE}/api/v1/hint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ submission_id: submissionId, tier, session_id: sessionId }),
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    let code: string | undefined;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      if (typeof body.code === "string") code = body.code;
    } catch {}
    const err = new Error(detail) as Error & { status: number; code?: string };
    err.status = response.status;
    err.code = code;
    throw err;
  }
  return await response.json();
}

export async function postSolutionRequest(submissionId: string, sessionId: string, _authToken: string) {
  const response = await fetch(`${API_BASE}/api/v1/solution-request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
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

/** Shared fetch utility for session-scoped GET requests — uses cookie auth. */
function sessionFetch(url: string, _ownerToken: string, init: RequestInit = {}): Promise<Response> {
  return fetch(url, {
    ...init,
    credentials: "include",
    headers: { ...(init.headers as Record<string, string> | undefined) },
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

export interface SessionHistoryItem {
  submission_id: string;
  timestamp: string;
  code_snippet: string;
  success: boolean;
  exception_type: string | null;
  concept_category: string | null;
}

export interface SessionHistoryResponse {
  items: SessionHistoryItem[];
  total: number;
}

export async function fetchSessionHistory(
  sessionId: string,
  ownerToken: string,
  q = "",
  limit = 20,
  offset = 0,
): Promise<SessionHistoryResponse> {
  const params = new URLSearchParams({ session_id: sessionId, limit: String(limit), offset: String(offset) });
  if (q.trim()) params.set("q", q.trim());
  const response = await sessionFetch(`${API_BASE}/api/v1/analytics/history?${params}`, ownerToken);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}
