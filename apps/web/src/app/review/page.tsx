"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { formatSeconds, LoadingBlock } from "@/components/LoadingBlock";
import {
  createSession,
  getSession,
  getSessionStatus,
  updateSession,
  runSessionAnalysis,
  type JoinColumnPair,
  type JoinSuggestion,
  type SessionDetail,
  type SessionStatus,
} from "@/lib/api";

function tierHint(tier?: string) {
  if (tier === "require_filter") return "Large dataset — add a filter or use the automatic sample.";
  if (tier === "recommend_filter") return "Medium dataset — consider a filter to focus the analysis.";
  return "Row cap and 5% sample apply when the table is large.";
}

function joinOnFromSuggestion(s: JoinSuggestion): JoinColumnPair[] {
  return s.left_keys.map((left, i) => ({ left, right: s.right_keys[i] ?? left }));
}

function formatOverlap(pct: number) {
  return `${Math.round(pct * 100)}%`;
}

function ReviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = (params.get("ids") ?? "").split(",").filter(Boolean);
  const [intent, setIntent] = useState("");
  const [ml, setMl] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(params.get("session"));
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [ingestStatus, setIngestStatus] = useState<SessionStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [joinOn, setJoinOn] = useState<JoinColumnPair[]>([]);
  const [starting, setStarting] = useState(false);
  const [booting, setBooting] = useState(true);

  const refreshSession = useCallback(async (id: string) => {
    const d = await getSession(id);
    setDetail(d);
    setFilters(d.config?.filters ?? {});
    setMl(d.config?.ml_enabled ?? true);
    if (d.config?.join_on?.length) {
      setJoinOn(d.config.join_on);
    } else if (d.preview?.join_suggestions?.length) {
      const ok = d.preview.join_suggestions.filter((s) => s.ok);
      const pick = ok.find((s) => s.auto_recommended) ?? ok[0];
      if (pick) setJoinOn(joinOnFromSuggestion(pick));
    } else if (d.config?.join_keys?.length) {
      setJoinOn(d.config.join_keys.map((k) => ({ left: k, right: k })));
    } else {
      setJoinOn([]);
    }
  }, []);

  // Create session once when arriving from search
  useEffect(() => {
    if (ids.length === 0) return;
    let cancelled = false;

    async function boot() {
      setBooting(true);
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
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "Could not start session");
      } finally {
        if (!cancelled) setBooting(false);
      }
    }

    boot();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- boot once per ids
  }, [ids.join(",")]);

  // Poll ingest progress until ready or failed
  useEffect(() => {
    if (!sessionId || booting) return;
    let cancelled = false;

    async function poll() {
      try {
        const status = await getSessionStatus(sessionId!);
        if (cancelled) return;
        setIngestStatus(status);

        if (status.status === "ready") {
          await refreshSession(sessionId!);
        } else if (status.status === "failed") {
          setLoadError(status.message ?? "Ingest failed");
        }
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "Could not reach API");
      }
    }

    poll();
    const interval = setInterval(poll, 800);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [sessionId, booting, refreshSession]);

  async function applyConfig() {
    if (!sessionId) return;
    const d = await updateSession(sessionId, {
      user_intent: intent || undefined,
      ml_enabled: ml,
      filters,
      join_on: joinOn.length ? joinOn : [],
      join_keys: joinOn.length ? joinOn.map((p) => p.left) : [],
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

  const isIngesting =
    booting ||
    !sessionId ||
    ingestStatus?.status === "ingesting" ||
    (detail?.status === "ingesting" && ingestStatus?.status !== "ready");

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

  if (isIngesting || !detail) {
    const message =
      ingestStatus?.message ??
      detail?.message ??
      (booting ? "Starting…" : "Loading your data…");
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <Link
          href={`/search?ids=${ids.join(",")}`}
          className="inline-block text-sm font-medium text-pink-600 hover:text-pink-700"
        >
          ← Back to search
        </Link>
        <h1 className="mb-6 mt-4 text-xl font-semibold text-stone-800">Loading datasets</h1>
        <LoadingBlock
          message={message}
          percent={ingestStatus?.percent ?? detail?.percent}
          timeHint={formatSeconds(ingestStatus?.estimate_remaining_sec)}
          minHeight="min-h-[32vh]"
        />
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
  const joinSuggestions = (detail.preview?.join_suggestions ?? []).filter((s) => s.ok);
  const twoDatasets = datasets.length >= 2;
  const selectedSuggestion = joinSuggestions.find(
    (s) =>
      joinOn.length > 0 &&
      s.left_keys.length === joinOn.length &&
      s.left_keys.every((k, i) => k === joinOn[i]?.left && s.right_keys[i] === joinOn[i]?.right),
  );
  const backHref = `/search?ids=${ids.join(",")}`;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link
        href={backHref}
        className="inline-block text-sm font-medium text-pink-600 hover:text-pink-700"
      >
        ← Back to search
      </Link>
      <h1 className="mt-4 text-2xl font-semibold text-stone-800">Review & confirm</h1>
      <p className="mt-1 text-sm text-stone-600">Estimated analysis time: 2–4 minutes</p>
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
              <details className="mt-2">
                <summary className="cursor-pointer text-xs font-medium text-pink-600 hover:text-pink-700">
                  Columns ({ds.columns.length})
                </summary>
                <ul className="mt-2 space-y-1 text-xs text-stone-600">
                  {ds.columns.map((col) => (
                    <li key={col.name}>
                      <span className="font-medium text-stone-800">{col.name}</span>
                      {col.type && <span className="text-stone-500"> · {col.type}</span>}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <details className="mt-2">
              <summary className="cursor-pointer text-xs font-medium text-pink-600 hover:text-pink-700">
                Filter{filters[String(idx)]?.trim() ? " (active)" : ""}
              </summary>
              <label className="mt-2 block text-xs text-stone-500">
                SQL WHERE clause (optional)
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
            </details>
          </li>
        ))}
      </ul>

      {twoDatasets && joinSuggestions.length > 0 && (
        <div className="mt-6 space-y-2">
          <label className="block text-sm font-medium text-stone-700">
            Join key (2 datasets)
          </label>
          <select
            value={
              joinOn.length === 0
                ? ""
                : JSON.stringify(joinOn)
            }
            onChange={(e) => {
              const v = e.target.value;
              const next = v ? (JSON.parse(v) as JoinColumnPair[]) : [];
              setJoinOn(next);
              if (sessionId) {
                updateSession(sessionId, {
                  join_on: next,
                  join_keys: next.map((p) => p.left),
                });
              }
            }}
            className="mt-1 w-full rounded-xl border border-[#ddd0c0] bg-white px-3 py-2 text-sm"
          >
            <option value="">Analyze separately (no join)</option>
            {joinSuggestions.map((s) => (
              <option key={s.label} value={JSON.stringify(joinOnFromSuggestion(s))}>
                {s.label}
                {s.auto_recommended ? " · recommended" : ""}
                {" · "}
                {s.matched_rows.toLocaleString()} rows · overlap{" "}
                {formatOverlap(s.overlap_left_pct)}/{formatOverlap(s.overlap_right_pct)}
              </option>
            ))}
          </select>
          {selectedSuggestion && (
            <p className="text-xs text-stone-500">
              {selectedSuggestion.matched_rows.toLocaleString()} joined rows ·{" "}
              {formatOverlap(selectedSuggestion.overlap_left_pct)} of left keys match ·{" "}
              {formatOverlap(selectedSuggestion.overlap_right_pct)} of right keys match
              {selectedSuggestion.auto_recommended && (
                <span className="text-pink-600"> · auto-selected (high confidence)</span>
              )}
            </p>
          )}
        </div>
      )}

      {twoDatasets && joinSuggestions.length === 0 && (
        <p className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          No safe join key found — datasets will be analyzed separately. Try aligning column names
          (e.g. country + year) or adding filters.
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
