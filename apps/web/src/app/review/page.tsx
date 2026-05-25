"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { LoadingBlock } from "@/components/LoadingBlock";
import {
  createSession,
  getSession,
  getSessionStatus,
  updateSession,
  runSessionAnalysis,
  type SessionDetail,
} from "@/lib/api";

function tierHint(tier?: string) {
  if (tier === "require_filter") return "Large dataset — add a filter or use the automatic sample.";
  if (tier === "recommend_filter") return "Medium dataset — consider a filter to focus the analysis.";
  return "Row cap and 5% sample apply when the table is large.";
}

function ReviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = (params.get("ids") ?? "").split(",").filter(Boolean);
  const [intent, setIntent] = useState("");
  const [ml, setMl] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(params.get("session"));
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [joinKeys, setJoinKeys] = useState<string[]>([]);
  const [starting, setStarting] = useState(false);

  const refreshSession = useCallback(async (id: string) => {
    const d = await getSession(id);
    setDetail(d);
    setFilters(d.config?.filters ?? {});
    if (d.config?.join_keys?.length) setJoinKeys(d.config.join_keys);
    else if (d.preview?.suggested_join_keys?.length)
      setJoinKeys([d.preview.suggested_join_keys[0]]);
  }, []);

  useEffect(() => {
    if (ids.length === 0) return;
    let cancelled = false;

    async function boot() {
      setLoadError(null);
      try {
        let sid = sessionId;
        if (!sid) {
          const created = await createSession(ids, intent || undefined, ml);
          sid = created.id;
          if (!cancelled) {
            setSessionId(sid);
            router.replace(`/review?ids=${ids.join(",")}&session=${sid}`);
          }
        }
        for (let i = 0; i < 120 && !cancelled; i++) {
          const status = await getSessionStatus(sid!);
          if (status.status === "ready") break;
          if (status.status === "failed") {
            throw new Error(status.message ?? "Ingest failed");
          }
          await new Promise((r) => setTimeout(r, 500));
        }
        if (!cancelled) await refreshSession(sid!);
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "Could not load session");
      }
    }

    boot();
    return () => {
      cancelled = true;
    };
  }, [ids.join(","), sessionId, refreshSession, router]);

  async function applyConfig() {
    if (!sessionId) return;
    const d = await updateSession(sessionId, {
      user_intent: intent || undefined,
      ml_enabled: ml,
      filters,
      join_keys: joinKeys.length ? joinKeys : undefined,
    });
    setDetail(d);
  }

  async function runAnalysis() {
    if (!sessionId) return;
    setStarting(true);
    try {
      await applyConfig();
      await runSessionAnalysis(sessionId);
      router.push(`/analyze?session=${sessionId}`);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Could not start analysis");
      setStarting(false);
    }
  }

  if (ids.length === 0) {
    return (
      <p className="text-sm text-stone-600">
        No datasets selected.{" "}
        <a href="/search" className="font-medium text-pink-600 hover:text-pink-700">
          Go back to search
        </a>
        .
      </p>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="rounded-xl border border-pink-200 bg-pink-50 px-3 py-2 text-sm text-pink-900">
          {loadError}
        </p>
        <a href="/search" className="mt-4 inline-block text-sm text-pink-600 hover:text-pink-700">
          Back to search
        </a>
      </div>
    );
  }

  if (!detail || detail.status === "ingesting") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <LoadingBlock message={detail?.message ?? "Loading your data…"} minHeight="min-h-[40vh]" />
      </div>
    );
  }

  if (starting) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <LoadingBlock message="Starting analysis…" minHeight="min-h-[40vh]" />
      </div>
    );
  }

  const datasets = detail.preview?.datasets ?? [];
  const suggested = detail.preview?.suggested_join_keys ?? [];
  const twoDatasets = datasets.length >= 2;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-stone-800">Review & confirm</h1>
      <p className="mt-1 text-sm text-stone-600">Estimated time: 2–4 minutes</p>
      <p className="mt-2 text-xs text-stone-500">{tierHint(detail.preview?.sampling_tier)}</p>

      <ul className="mt-6 space-y-3">
        {datasets.map((ds, idx) => (
          <li key={ds.resource_id} className="rounded-xl border border-[#e8ddd0] bg-white p-4 text-sm">
            <p className="font-medium text-stone-800">{ds.title}</p>
            <p className="mt-1 text-stone-600">
              {ds.row_count.toLocaleString()} rows loaded
              {ds.analysis_n != null && (
                <> · analyzing {ds.analysis_n.toLocaleString()} rows</>
              )}
            </p>
            {ds.columns && ds.columns.length > 0 && (
              <p className="mt-2 text-xs text-stone-500">
                Columns: {ds.columns.slice(0, 8).map((c) => c.name).join(", ")}
                {ds.columns.length > 8 ? "…" : ""}
              </p>
            )}
            <label className="mt-3 block text-xs font-medium text-stone-600">
              Filter (SQL WHERE clause, optional)
              <input
                value={filters[String(idx)] ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, [String(idx)]: e.target.value }))
                }
                onBlur={applyConfig}
                placeholder="e.g. state = 'CA'"
                className="mt-1 w-full rounded-lg border border-[#ddd0c0] bg-white px-2 py-1.5 text-sm text-stone-800"
              />
            </label>
          </li>
        ))}
      </ul>

      {twoDatasets && suggested.length > 0 && (
        <label className="mt-6 block text-sm font-medium text-stone-700">
          Join key (2 datasets)
          <select
            value={joinKeys[0] ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              setJoinKeys(v ? [v] : []);
              if (sessionId) updateSession(sessionId, { join_keys: v ? [v] : [] });
            }}
            className="mt-1 w-full rounded-xl border border-[#ddd0c0] bg-white px-3 py-2"
          >
            <option value="">— select column —</option>
            {suggested.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
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
        Include ML insights (clustering & anomalies)
      </label>
      <p className="mt-6 text-xs text-stone-500">
        Correlation does not imply causation. Large datasets use a disclosed random sample (seed 42).
      </p>
      <button
        type="button"
        onClick={runAnalysis}
        className="mt-8 rounded-xl bg-pink-600 px-6 py-3 text-sm font-semibold text-white hover:bg-pink-700"
      >
        Run analysis
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
