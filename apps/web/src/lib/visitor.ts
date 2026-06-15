const STORAGE_KEY = "findings_visitor_id";

export function getVisitorId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  } catch {
    return null;
  }
}

export async function recordVisit(path: string): Promise<void> {
  const visitorId = getVisitorId();
  if (!visitorId) return;

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  await fetch(`${base}/metrics/visit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ visitor_id: visitorId, path }),
    keepalive: true,
  });
}
