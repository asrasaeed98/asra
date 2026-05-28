/** Plain-language labels and helpers for finding cards. */

export const FINDING_TYPE_LABELS: Record<string, string> = {
  spearman_correlation: "Related trends",
  group_comparison: "Group difference",
  chi_square: "Category link",
  time_trend: "Change over time",
  descriptive: "Data summary",
  kmeans_cluster: "Clusters",
  dbscan_cluster: "Density clusters",
  pca_structure: "Numeric structure",
  anomaly_top_rows: "Unusual rows",
  lof_anomaly: "Local outliers",
  // legacy aliases
  kmeans_clusters: "Clusters",
  isolation_forest: "Unusual rows",
};

export function findingTypeLabel(type: string): string {
  return FINDING_TYPE_LABELS[type] ?? type.replace(/_/g, " ");
}

/** Plain-language explanation of the analysis type shown on result cards. */
export function findingTypeDescription(type: string): string | null {
  switch (type) {
    case "group_comparison":
      return "Compares a numeric measure (like grant amount) across categories (like program area).";
    case "spearman_correlation":
      return "Checks whether two numeric columns tend to rise or fall together — or move in opposite directions.";
    case "time_trend":
      return "Looks for a general increase or decrease in a value across dates or time periods.";
    case "chi_square":
      return "Tests whether two category fields are linked — some combinations show up more often than you'd expect by chance.";
    case "descriptive":
      return "Summarizes the dataset without a significance test — useful context when no strong pattern was found.";
    case "kmeans_cluster":
    case "kmeans_clusters":
      return "Groups similar rows together based on their numeric values.";
    case "dbscan_cluster":
      return "Finds dense groups in numeric space without fixing the number of clusters upfront.";
    case "pca_structure":
      return "Shows how much of the numeric variation can be captured by a single combined measure.";
    case "anomaly_top_rows":
    case "isolation_forest":
      return "Flags rows that look unusual compared with the rest of the dataset.";
    case "lof_anomaly":
      return "Flags rows that are unusual compared with their nearest neighbors.";
    default:
      return null;
  }
}

/** One-line plain English for common test types (fallback until AI summary). */
export function findingPlainIntro(type: string): string | null {
  switch (type) {
    case "group_comparison":
      return "A number you measured looks different across groups in the data.";
    case "spearman_correlation":
      return "Two numeric columns tend to move together (or in opposite directions).";
    case "time_trend":
      return "A value generally rises or falls over time.";
    case "chi_square":
      return "Two category columns appear linked — certain combinations show up more often.";
    case "descriptive":
      return "A quick summary of the dataset without a significance test.";
    default:
      return null;
  }
}

export function formatPValue(p: number | null): string {
  if (p == null) return "—";
  if (p < 0.001) return "< 0.001";
  return p.toFixed(3);
}

export function confidenceLabel(p: number | null): string | null {
  if (p == null) return null;
  if (p < 0.001) return "Very strong evidence";
  if (p < 0.01) return "Strong evidence";
  if (p < 0.05) return "Moderate evidence";
  return null;
}
