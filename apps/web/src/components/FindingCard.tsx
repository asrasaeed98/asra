"use client";

import { confidenceLabel, findingTypeDescription, findingTypeLabel, formatPValue } from "@/lib/finding-labels";

type Props = {
  finding: Finding;
  compact?: boolean;
  rank?: number;
};

function detailStr(finding: Finding, key: string): string | undefined {
  const v = finding.details?.[key];
  return typeof v === "string" ? v : undefined;
}

function AnalysisTypeLabel({ type }: { type: string }) {
  const label = findingTypeLabel(type);
  const description = findingTypeDescription(type);

  return (
    <span className="inline-flex items-center gap-1.5">
      {label}
      {description && (
        <span className="relative inline-flex">
          <button
            type="button"
            className="peer inline-flex rounded-full text-stone-400 transition-colors hover:text-pink-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pink-300"
            aria-label={`What ${label} means`}
          >
            <InfoIcon />
          </button>
          <span
            role="tooltip"
            className="pointer-events-none absolute left-1/2 top-full z-20 mt-1.5 hidden w-56 -translate-x-1/2 rounded-lg border border-[#e8ddd0] bg-white px-2.5 py-2 text-left text-[11px] font-normal normal-case leading-relaxed tracking-normal text-stone-600 shadow-md peer-hover:block peer-focus-visible:block"
          >
            {description}
          </span>
        </span>
      )}
    </span>
  );
}

function InfoIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-3.5 w-3.5"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export function FindingCard({ finding, compact = false, rank }: Props) {
  const headline = detailStr(finding, "headline") ?? finding.title;
  const impact = detailStr(finding, "impact");
  const technicalTitle = detailStr(finding, "technical_title");
  const confidence = confidenceLabel(finding.p_value);
  const isStatistical = finding.type !== "descriptive" && finding.p_value != null;

  return (
    <article className="rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm">
      <div className="flex items-start gap-3">
        {rank != null && (
          <span
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-pink-100 text-xs font-bold text-pink-700"
            aria-label={`Rank ${rank}`}
          >
            {rank}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-pink-600">
            <AnalysisTypeLabel type={finding.type} />
          </p>
          <h3 className="mt-1 text-sm font-semibold leading-snug text-stone-800">{headline}</h3>

          {impact && (
            <p className="mt-2 text-sm leading-relaxed text-stone-700">{impact}</p>
          )}

          {isStatistical && (
            <p className="mt-3 text-xs text-stone-500">
              Based on {finding.n.toLocaleString()} rows
              {confidence && <> · {confidence}</>}
            </p>
          )}

          {!compact && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-pink-600 hover:text-pink-700">
                View technical details
              </summary>
              {technicalTitle && technicalTitle !== headline && (
                <p className="mt-2 text-xs text-stone-500">{technicalTitle}</p>
              )}
              <dl className="mt-3 grid grid-cols-2 gap-2 border-t border-[#f0e8de] pt-3 text-xs text-stone-600">
                <div>
                  <dt className="text-stone-400">Sample size (n)</dt>
                  <dd>{finding.n.toLocaleString()} rows</dd>
                </div>
                {finding.p_value != null && (
                  <div>
                    <dt className="text-stone-400">p-value</dt>
                    <dd>{formatPValue(finding.p_value)}</dd>
                  </div>
                )}
                {finding.value != null && (
                  <div>
                    <dt className="text-stone-400">Effect size</dt>
                    <dd>{finding.value}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-stone-400">Method</dt>
                  <dd>{finding.method}</dd>
                </div>
                {finding.columns.length > 0 && (
                  <div className="col-span-2">
                    <dt className="text-stone-400">Fields</dt>
                    <dd>{finding.columns.join(", ")}</dd>
                  </div>
                )}
              </dl>
              {finding.caveat && <p className="mt-2 text-xs text-stone-500">{finding.caveat}</p>}
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-stone-500">Show SQL</summary>
                <pre className="mt-2 overflow-x-auto rounded-lg bg-[#faf8f5] p-2 text-xs text-stone-600">
                  {finding.sql}
                </pre>
              </details>
            </details>
          )}
        </div>
      </div>
    </article>
  );
}

export function DatasetDetailsPanel({
  datasets,
  glossary,
}: {
  datasets: Array<{
    title: string;
    n_rows: number;
    numeric_columns: string[];
    categorical_columns: string[];
    datetime_columns: string[];
  }>;
  glossary: Array<{ name: string; label: string; description?: string | null }>;
}) {
  const glossaryByName = new Map(glossary.map((e) => [e.name.toLowerCase(), e]));
  const hasContent =
    datasets.length > 0 ||
    glossary.some((e) => e.description || e.label !== e.name);

  if (!hasContent) return null;

  return (
    <details className="mt-3">
      <summary className="cursor-pointer text-xs font-medium text-pink-600 hover:text-pink-700">
        Fields analyzed & data dictionary
      </summary>
      <div className="mt-2 space-y-4 border-t border-[#f0e8de] pt-3">
        {datasets.map((ds) => (
          <div key={ds.title} className="text-xs text-stone-600">
            <p className="font-medium text-stone-800">
              {ds.title} ({ds.n_rows.toLocaleString()} rows)
            </p>
            {ds.numeric_columns.length > 0 && (
              <FieldList label="Numeric" names={ds.numeric_columns} glossaryByName={glossaryByName} />
            )}
            {ds.categorical_columns.length > 0 && (
              <FieldList label="Categories" names={ds.categorical_columns} glossaryByName={glossaryByName} />
            )}
            {ds.datetime_columns.length > 0 && (
              <FieldList label="Dates" names={ds.datetime_columns} glossaryByName={glossaryByName} />
            )}
          </div>
        ))}
      </div>
    </details>
  );
}

function FieldList({
  label,
  names,
  glossaryByName,
}: {
  label: string;
  names: string[];
  glossaryByName: Map<string, { name: string; label: string; description?: string | null }>;
}) {
  return (
    <div className="mt-2">
      <p className="text-stone-500">{label}</p>
      <ul className="mt-1 space-y-1.5">
        {names.map((name) => {
          const entry = glossaryByName.get(name.toLowerCase());
          return (
            <li key={name}>
              <span className="font-medium text-stone-800">{entry?.label ?? name}</span>
              {entry?.description && (
                <span className="text-stone-600"> — {entry.description}</span>
              )}
              {!entry?.description && entry?.label && entry.label !== name && (
                <span className="text-stone-400"> ({name})</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function MetricsGuide() {
  return (
    <details className="rounded-xl border border-[#e8ddd0] bg-[#faf8f5] px-4 py-3">
      <summary className="cursor-pointer text-sm font-medium text-stone-700">
        What do these numbers mean?
      </summary>
      <dl className="mt-3 space-y-3 text-xs leading-relaxed text-stone-600">
        <div>
          <dt className="font-medium text-stone-800">Sample size (n)</dt>
          <dd className="mt-0.5">How many rows were included after leaving out blanks.</dd>
        </div>
        <div>
          <dt className="font-medium text-stone-800">p-value</dt>
          <dd className="mt-0.5">
            How surprising the pattern would be if nothing were really going on. Lower is stronger.
          </dd>
        </div>
        <div>
          <dt className="font-medium text-stone-800">Effect size</dt>
          <dd className="mt-0.5">How large the pattern is — bigger usually matters more in practice.</dd>
        </div>
      </dl>
    </details>
  );
}

