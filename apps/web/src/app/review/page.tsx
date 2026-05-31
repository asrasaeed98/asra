"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { LoadingBlock } from "@/components/LoadingBlock";
import { formatRowCount, portalLabel, ANALYSIS_ROW_CAP, LARGE_DOWNLOAD_ROW_HINT, MAX_DOWNLOAD_MB } from "@/lib/catalog-labels";
import {
  createSession,
  getDatasetsBatch,
  getGuidedPath,
  runSessionAnalysis,
  updateSession,
  type CatalogResult,
  type JoinColumnPair,
} from "@/lib/api";

function samplingHint(rowHint: number | null | undefined) {
  if (rowHint == null) return "Row cap and 5% sample apply for large tables.";
  if (rowHint > 1_000_000) return "Large dataset — analysis uses a random sample (seed 42).";
  if (rowHint > ANALYSIS_ROW_CAP) return "Medium dataset — analysis uses up to 100,000 rows.";
  return "Full table used when row count is modest.";
}

function ReviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = (params.get("ids") ?? "").split(",").filter(Boolean).slice(0, 2);
  const pairId = params.get("pair");
  const intentParam = params.get("intent") ?? "";
  const [intent, setIntent] = useState(intentParam);
  const [ml, setMl] = useState(true);
  const [catalogs, setCatalogs] = useState<CatalogResult[]>([]);
  const [joinOn, setJoinOn] = useState<JoinColumnPair[]>([]);
  const [joinLabel, setJoinLabel] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setIntent(intentParam);
  }, [intentParam]);

  useEffect(() => {
    if (ids.length === 0) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setLoadError(null);
      try {
        const rows = await getDatasetsBatch(ids);
        if (cancelled) return;
        setCatalogs(rows);

        if (pairId) {
          const path = await getGuidedPath(pairId);
          if (cancelled) return;
          if (path.user_intent) setIntent(path.user_intent);
          if (path.join_hint.length) {
            setJoinOn(path.join_hint);
            setJoinLabel(path.title);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "Could not load datasets");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [ids.join(","), pairId]);

  async function runAnalysis() {
    setStarting(true);
    setLoadError(null);
    try {
      const created = await createSession(ids, intent.trim() || undefined, ml);
      await updateSession(created.id, {
        user_intent: intent.trim() || undefined,
        ml_enabled: ml,
        join_on: joinOn.length ? joinOn : [],
        join_keys: joinOn.length ? joinOn.map((p) => p.left) : [],
      });
      await runSessionAnalysis(created.id);
      router.push(`/analyze?session=${created.id}`);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Could not start analysis");
      setStarting(false);
    }
  }

  if (ids.length === 0) {
    return (
      <p className="text-sm text-stone-600">
        No datasets selected.{" "}
        <Link href="/search" className="font-medium text-pink-600 hover:text-pink-700">
          Go back to search
        </Link>
        .
      </p>
    );
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <LoadingBlock message="Loading dataset details…" minHeight="min-h-[32vh]" />
      </div>
    );
  }

  if (loadError && catalogs.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="rounded-xl border border-pink-200 bg-pink-50 px-3 py-2 text-sm text-pink-900">
          {loadError}
        </p>
        <Link href="/search" className="mt-4 inline-block text-sm text-pink-600 hover:text-pink-700">
          Back to search
        </Link>
      </div>
    );
  }

  const twoDatasets = catalogs.length >= 2;
  const backHref = `/search?ids=${ids.join(",")}`;
  const maxRowHint = Math.max(...catalogs.map((c) => c.row_count_hint ?? 0));
  const largeDownload = maxRowHint >= LARGE_DOWNLOAD_ROW_HINT;
  const timeEstimate = largeDownload ? "3–6 minutes" : "2–4 minutes";

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href={backHref}
        className="inline-block text-sm font-medium text-pink-600 hover:text-pink-700"
      >
        ← Back to search
      </Link>
      <h1 className="mt-4 text-2xl font-semibold text-stone-800">Review & confirm</h1>
      <p className="mt-1 text-sm text-stone-600">
        Confirm your choices, then we&apos;ll download the data and run analysis in one step (usually{" "}
        {timeEstimate}).
      </p>
      {largeDownload && (
        <p className="mt-3 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs leading-relaxed text-sky-950">
          Large dataset selected — download may take a few minutes (up to {MAX_DOWNLOAD_MB}MB for NYC
          tables). Keep this tab open while loading; progress updates on the next screen.
        </p>
      )}
      <p className="mt-2 text-xs text-stone-500">{samplingHint(maxRowHint || null)}</p>

      <ul className="mt-6 space-y-3">
        {catalogs.map((ds) => {
          const rowLabel = formatRowCount(ds.row_count_hint);
          return (
            <li
              key={ds.id}
              className="rounded-xl border border-[#e8ddd0] bg-white p-4 text-sm shadow-sm"
            >
              <p className="font-medium text-stone-800">{ds.title}</p>
              {ds.organization && (
                <p className="mt-1 text-stone-600">{ds.organization}</p>
              )}
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-stone-500">
                <span className="rounded-full border border-[#e8ddd0] bg-[#faf6f0] px-2 py-0.5">
                  {portalLabel(ds.portal)}
                </span>
                {rowLabel && (
                  <span className="rounded-full border border-emerald-100 bg-emerald-50 px-2 py-0.5 text-emerald-800">
                    ~{rowLabel} rows
                  </span>
                )}
              </div>
              {ds.columns && ds.columns.length > 0 && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs font-medium text-pink-600 hover:text-pink-700">
                    Columns ({ds.columns.length})
                  </summary>
                  <ul className="mt-2 space-y-1 text-xs text-stone-600">
                    {ds.columns.slice(0, 12).map((col) => (
                      <li key={col.name}>
                        <span className="font-medium text-stone-800">{col.name}</span>
                        {col.type && <span className="text-stone-500"> · {col.type}</span>}
                      </li>
                    ))}
                    {ds.columns.length > 12 && (
                      <li className="text-stone-400">+ {ds.columns.length - 12} more</li>
                    )}
                  </ul>
                </details>
              )}
              {(ds.attribution_text || ds.license_display) && (
                <p className="mt-2 text-xs leading-relaxed text-stone-500">
                  {ds.license_display && (
                    <span className="block text-stone-600">{ds.license_display}</span>
                  )}
                  {ds.attribution_text}
                </p>
              )}
            </li>
          );
        })}
      </ul>

      {twoDatasets && joinOn.length > 0 && (
        <div className="mt-6 rounded-xl border border-violet-200 bg-violet-50/50 px-4 py-3 text-sm">
          <p className="font-medium text-violet-900">Curated join</p>
          <p className="mt-1 text-violet-800">
            {joinLabel ? `${joinLabel}: ` : ""}
            {joinOn.map((p) => `${p.left} ↔ ${p.right}`).join(", ")}
          </p>
        </div>
      )}

      {twoDatasets && joinOn.length === 0 && (
        <p className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Two datasets selected — we&apos;ll try to find a safe join key automatically, or analyze
          them separately if none is found.
        </p>
      )}

      <label className="mt-6 block text-sm font-medium text-stone-700">
        What are you trying to learn? (optional)
        <input
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="mt-1 w-full rounded-xl border border-[#ddd0c0] bg-white px-3 py-2 focus:border-pink-300 focus:ring-2 focus:ring-pink-100"
          placeholder="e.g. housing vs income by state"
        />
      </label>

      <label className="mt-4 flex items-center gap-2 text-sm text-stone-700">
        <input
          type="checkbox"
          checked={ml}
          onChange={(e) => setMl(e.target.checked)}
          className="accent-pink-500"
        />
        Include ML insights (clustering, PCA & anomaly detection)
      </label>

      <p className="mt-6 text-xs text-stone-500">
        Correlation does not imply causation. Large datasets use a disclosed random sample (seed 42).
      </p>

      {loadError && (
        <p className="mt-4 rounded-xl border border-pink-200 bg-pink-50 px-3 py-2 text-sm text-pink-900">
          {loadError}
        </p>
      )}

      <button
        type="button"
        onClick={runAnalysis}
        disabled={starting}
        className="mt-8 rounded-xl bg-pink-600 px-6 py-3 text-sm font-semibold text-white hover:bg-pink-700 disabled:opacity-50"
      >
        {starting ? "Starting…" : "Run analysis"}
      </button>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<LoadingBlock message="Loading review…" minHeight="min-h-[40vh]" />}>
      <ReviewContent />
    </Suspense>
  );
}
