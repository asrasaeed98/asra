export function formatRowCount(count?: number | null): string | null {
  if (count == null || count <= 0) return null;
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
    default:
      return portal;
  }
}
