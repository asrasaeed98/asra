const PROD_API = "https://asra-production.up.railway.app";

function isLocalDevHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function resolveApiBase(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL;
  if (fromEnv) {
    return fromEnv;
  }
  if (typeof window !== "undefined") {
    const { hostname } = window.location;
    if (!isLocalDevHost(hostname)) {
      return PROD_API;
    }
  } else if (process.env.VERCEL || process.env.NODE_ENV === "production") {
    return PROD_API;
  }
  return "http://127.0.0.1:8000";
}

function getApiBase(): string {
  return resolveApiBase();
}

function isLocalDev(): boolean {
  if (typeof window !== "undefined") {
    return isLocalDevHost(window.location.hostname);
  }
  return process.env.NODE_ENV === "development";
}

function networkErrorMessage(path: string): string {
  const base = getApiBase();
  if (isLocalDev()) {
    return (
      `Could not reach the API at ${base}${path}. ` +
      "Start the API on port 8000 and open the app at http://127.0.0.1:3000."
    );
  }
  return (
    `Could not reach the API at ${base}${path}. ` +
    "Check your connection and try again. During analysis, keep this tab open — large datasets can take a few minutes."
  );
}

export type CatalogResult = {
  id: string;
  portal: string;
  title: string;
  description?: string;
  organization?: string;
  tags: string[];
  format?: string;
  license_normalized: string;
  license_display: string;
  attribution_required: boolean;
  attribution_text: string;
  publisher: string;
  source_url: string;
  resource_url?: string;
  byte_size?: number;
  row_count_hint?: number | null;
  columns?: { name: string; type?: string }[];
  relevance_score?: number | null;
  quality_score?: number | null;
  match_reason?: string | null;
};

export type SearchResponse = {
  query: string;
  topic?: string | null;
  page: number;
  limit: number;
  total: number;
  results: CatalogResult[];
  message?: string;
};

export type Finding = {
  id: string;
  type: string;
  title: string;
  columns: string[];
  value: number | null;
  p_value: number | null;
  n: number;
  method: string;
  caveat: string;
  sql: string;
  datasets: string[];
  details?: Record<string, unknown>;
};

export type SessionResults = {
  session_id: string;
  status: string;
  phase?: string;
  percent?: number;
  findings: Finding[];
  display_finding_ids?: string[];
  column_glossary?: Array<{ name: string; label: string; description?: string | null }>;
  charts: Array<{ id: string; finding_id: string; type: string; title: string; spec: Record<string, unknown> }>;
  join_report?: Record<string, unknown> | null;
  analysis_report?: {
    tests_planned: number;
    statistical_findings: number;
    display_limit?: number;
    display_count?: number;
    total_findings: number;
    methods_run?: string[];
    ml_enabled?: boolean;
    datasets: Array<{
      title: string;
      n_rows: number;
      numeric_columns: string[];
      categorical_columns: string[];
      datetime_columns: string[];
    }>;
    notes: string[];
    measure_notes?: Array<{
      column?: string;
      label?: string;
      source?: string;
      disclosure?: string;
      ai_inferred?: string;
    }>;
  };
  ai_summary: string | null;
  ai_summary_blocks?: Array<
    | { type: "header"; text: string }
    | { type: "paragraph"; text: string }
    | { type: "list"; items: string[] }
  > | null;
  ai_summary_source?: "anthropic" | "template" | "unavailable" | string | null;
  ai_summary_fallback_reason?: string | null;
  chat?: ChatState;
  message?: string;
  updated_at?: string;
  catalogs?: CatalogResult[];
};

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type ChatState = {
  messages: ChatTurn[];
  questions_used: number;
  questions_remaining: number;
  max_questions: number;
  ai_paused?: boolean;
};

export type ChatResponse = {
  reply: string;
  questions_used: number;
  questions_remaining: number;
  limit_reached: boolean;
  grounded: boolean;
  ai_paused?: boolean;
  messages: ChatTurn[];
};

export type JoinSuggestion = {
  keys: string[];
  left_keys: string[];
  right_keys: string[];
  label: string;
  matched_rows: number;
  overlap_left_pct: number;
  overlap_right_pct: number;
  score: number;
  ok: boolean;
  warning?: string | null;
  auto_recommended?: boolean;
};

export type JoinColumnPair = { left: string; right: string };

export type SessionResponse = {
  id: string;
  status: string;
  resource_ids: string[];
};

export type SessionStatus = {
  session_id: string;
  status: string;
  phase: string;
  message?: string;
  percent: number;
  row_counts?: Record<string, number>;
  estimate_remaining_sec?: number;
  updated_at?: string;
};

export type SessionDetail = {
  id: string;
  status: string;
  phase: string;
  message?: string;
  percent: number;
  resource_ids: string[];
  user_intent?: string;
  config: {
    ml_enabled?: boolean;
    filters?: Record<string, string>;
    join_keys?: string[];
    join_on?: JoinColumnPair[];
  };
  row_counts?: Record<string, number>;
  preview?: {
    datasets?: Array<{
      resource_id: string;
      title: string;
      row_count: number;
      analysis_n?: number;
      filtered_row_count?: number;
      columns?: Array<{ name: string; type: string }>;
    }>;
    suggested_join_keys?: string[];
    join_suggestions?: JoinSuggestion[];
    sampling_tier?: string;
    analysis_row_counts?: Record<string, number>;
  };
  error?: string;
  catalogs: CatalogResult[];
};

export async function apiGet<T>(path: string, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${getApiBase()}${path}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out — the API may be busy. Try again in a moment.");
    }
    if (err instanceof TypeError) {
      throw new Error(networkErrorMessage(path));
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${getApiBase()}${path}`, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof TypeError) {
      throw new Error(networkErrorMessage(path));
    }
    throw err;
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API ${path}: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

export type SearchTopic = {
  id: string;
  title: string;
  description: string;
  icon: string;
  dataset_count: number;
  path_count: number;
};

export function getSearchTopics() {
  return apiGet<SearchTopic[]>("/search/topics");
}

export function searchDatasets(q: string, portal?: string, page = 1, topic?: string) {
  const params = new URLSearchParams({ q, page: String(page) });
  if (portal) params.set("portal", portal);
  if (topic) params.set("topic", topic);
  return apiGet<SearchResponse>(`/search?${params}`);
}

export function getDatasetsBatch(resourceIds: string[]) {
  const params = new URLSearchParams({ ids: resourceIds.join(",") });
  return apiGet<CatalogResult[]>(`/datasets/batch?${params}`);
}

export function createSession(resourceIds: string[], userIntent?: string, mlEnabled = true) {
  return apiPost<SessionResponse>("/sessions", {
    resource_ids: resourceIds,
    user_intent: userIntent || null,
    ml_enabled: mlEnabled,
  });
}

export function getSession(sessionId: string) {
  return apiGet<SessionDetail>(`/sessions/${sessionId}`);
}

export function getSessionStatus(sessionId: string) {
  return apiGet<SessionStatus>(`/sessions/${sessionId}/status`, 60_000);
}

export function updateSession(
  sessionId: string,
  patch: {
    user_intent?: string;
    ml_enabled?: boolean;
    filters?: Record<string, string>;
    join_keys?: string[];
    join_on?: JoinColumnPair[];
  },
) {
  return apiPatch<SessionDetail>(`/sessions/${sessionId}`, patch);
}

export function runSessionAnalysis(sessionId: string) {
  return apiPost<{ session_id: string; status: string; phase: string }>(
    `/sessions/${sessionId}/run`,
  );
}

export function getSessionResults(sessionId: string) {
  return apiGet<SessionResults>(`/sessions/${sessionId}/results`);
}

export function sendSessionChat(sessionId: string, message: string) {
  return apiPost<ChatResponse>(`/sessions/${sessionId}/chat`, { message });
}

export async function triggerCatalogSync(): Promise<{
  indexed: Record<string, number>;
  message: string;
}> {
  const res = await fetch(`${getApiBase()}/admin/sync`, { method: "POST" });
  if (!res.ok) throw new Error(`Sync failed: ${res.status}`);
  return res.json();
}

export type GuidedTopic = {
  id: string;
  title: string;
  description: string;
  icon: string;
  path_count: number;
};

export type GuidedPathPair = {
  path_id: string;
  title: string;
  topic: string;
  quality: string;
  description: string;
  user_intent: string;
  resource_ids: string[];
  join_hint: JoinColumnPair[];
  why: string;
  datasets: CatalogResult[];
};

export type GuidedSuggestResponse = {
  query: string;
  topic: string | null;
  paraphrase: string | null;
  recommended_pairs: GuidedPathPair[];
  datasets: CatalogResult[];
  fallback_message: string | null;
};

export function getGuidedTopics() {
  return apiGet<GuidedTopic[]>("/guided/topics");
}

export function getGuidedPaths(topic?: string) {
  const params = topic ? `?topic=${encodeURIComponent(topic)}` : "";
  return apiGet<GuidedPathPair[]>(`/guided/paths${params}`);
}

export function guidedSuggest(q: string, topic?: string) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (topic) params.set("topic", topic);
  return apiGet<GuidedSuggestResponse>(`/guided/suggest?${params}`);
}

export function getGuidedPath(pathId: string) {
  return apiGet<GuidedPathPair>(`/guided/paths/${encodeURIComponent(pathId)}`);
}
