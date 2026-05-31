export const ANALYSIS_ROW_CAP = 100_000;
export const LARGE_DOWNLOAD_ROW_HINT = 50_000;
export const MAX_DOWNLOAD_MB = 100;

export function formatRowCount(count?: number | null, analysisMax = ANALYSIS_ROW_CAP): string | null {
  if (count == null || count <= 0) return null;
  if (count > analysisMax) {
    return `~${analysisMax.toLocaleString()} rows max`;
  }
  return `~${count.toLocaleString()} rows`;
}

export function portalLabel(portal: string): string {
  switch (portal) {
    case "data_gov":
      return "data.gov";
    case "world_bank":
      return "World Bank";
    case "fred":
      return "FRED";
    case "nyc_open_data":
      return "NYC Open Data";
    default:
      return portal;
  }
}

/** Tailwind classes for source badges on result cards. */
export function portalBadgeClass(portal: string): string {
  switch (portal) {
    case "nyc_open_data":
      return "border-sky-200 bg-sky-50 text-sky-900";
    case "world_bank":
      return "border-blue-100 bg-blue-50 text-blue-900";
    case "fred":
      return "border-violet-100 bg-violet-50 text-violet-900";
    default:
      return "border-[#e8ddd0] bg-[#faf6f0] text-stone-600";
  }
}
