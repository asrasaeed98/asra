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

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

export function searchDatasets(q: string, portal?: string, page = 1) {
  const params = new URLSearchParams({ q, page: String(page) });
  if (portal) params.set("portal", portal);
  return apiGet<SearchResponse>(`/search?${params}`);
}

export async function triggerCatalogSync(): Promise<{
  indexed: Record<string, number>;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/admin/sync`, { method: "POST" });
  if (!res.ok) throw new Error(`Sync failed: ${res.status}`);
  return res.json();
}
