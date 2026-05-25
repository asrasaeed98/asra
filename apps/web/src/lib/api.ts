const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${path}: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export type SearchResponse = {
  query: string;
  page: number;
  limit: number;
  total: number;
  results: unknown[];
  message?: string;
};

export function searchDatasets(q: string, page = 1) {
  const params = new URLSearchParams({ q, page: String(page) });
  return apiGet<SearchResponse>(`/search?${params}`);
}

export function healthCheck() {
  return apiGet<{ status: string; version: string }>("/health");
}
