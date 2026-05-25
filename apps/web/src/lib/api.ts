const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
};

export type SearchResponse = {
  query: string;
  page: number;
  limit: number;
  total: number;
  results: CatalogResult[];
  message?: string;
};

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
    sampling_tier?: string;
    analysis_row_counts?: Record<string, number>;
  };
  error?: string;
  catalogs: CatalogResult[];
};

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API ${path}: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

export function searchDatasets(q: string, portal?: string, page = 1) {
  const params = new URLSearchParams({ q, page: String(page) });
  if (portal) params.set("portal", portal);
  return apiGet<SearchResponse>(`/search?${params}`);
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
  return apiGet<SessionStatus>(`/sessions/${sessionId}/status`);
}

export function updateSession(
  sessionId: string,
  patch: {
    user_intent?: string;
    ml_enabled?: boolean;
    filters?: Record<string, string>;
    join_keys?: string[];
  },
) {
  return apiPatch<SessionDetail>(`/sessions/${sessionId}`, patch);
}

export function runSessionAnalysis(sessionId: string) {
  return apiPost<{ session_id: string; status: string; phase: string }>(
    `/sessions/${sessionId}/run`,
  );
}

export async function triggerCatalogSync(): Promise<{
  indexed: Record<string, number>;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/admin/sync`, { method: "POST" });
  if (!res.ok) throw new Error(`Sync failed: ${res.status}`);
  return res.json();
}
