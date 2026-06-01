export function secondsSince(iso?: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.floor((Date.now() - t) / 1000));
}

export function formatLastUpdated(iso?: string | null): string | undefined {
  const sec = secondsSince(iso);
  if (sec == null) return undefined;
  if (sec < 5) return "Updated just now";
  if (sec < 60) return `Updated ${sec}s ago`;
  const mins = Math.floor(sec / 60);
  return mins === 1 ? "Updated 1 min ago" : `Updated ${mins} min ago`;
}

export function stuckWarning(iso?: string | null, active?: boolean): string | undefined {
  if (!active) return undefined;
  const sec = secondsSince(iso);
  if (sec == null || sec < 45) return undefined;
  return "This step is taking longer than usual — still checking…";
}
