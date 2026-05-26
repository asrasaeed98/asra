"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { DatasetDetailsPanel, FindingCard, MetricsGuide } from "@/components/FindingCard";
import { KeyFindingsContent } from "@/components/KeyFindingsContent";
import { LoadingBlock } from "@/components/LoadingBlock";
import { getSessionResults, type Finding, type SessionResults } from "@/lib/api";
import { formatSummaryBlocks } from "@/lib/summary-format";

function resolveDisplayFindings(data: SessionResults): { top: Finding[]; rest: Finding[] } {
  const all = data.findings ?? [];
  const ids = data.display_finding_ids ?? [];
  if (ids.length === 0) {
    const limit = data.analysis_report?.display_limit ?? 5;
    return { top: all.slice(0, limit), rest: all.slice(limit) };
  }
  const idSet = new Set(ids);
  const top = ids.map((id) => all.find((f) => f.id === id)).filter(Boolean) as Finding[];
  const rest = all.filter((f) => !idSet.has(f.id));
  return { top, rest };
}

function ResultsContent() {
  const params = useSearchParams();
  const sessionId = params.get("session") ?? "";
  const [data, setData] = useState<SessionResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    async function load() {
      try {
        const res = await getSessionResults(sessionId);
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load results");
      }
    }

    load();
    const t = setInterval(load, 2000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [sessionId]);

  const { top, rest } = useMemo(() => (data ? resolveDisplayFindings(data) : { top: [], rest: [] }), [data]);
  const summaryBlocks = useMemo(
    () => formatSummaryBlocks(data?.ai_summary, data?.ai_summary_blocks),
    [data?.ai_summary, data?.ai_summary_blocks],
  );

  if (!sessionId) {
    return (
      <p className="text-sm text-stone-600">
        Missing session.{" "}
        <Link href="/search" className="text-pink-600 hover:text-pink-700">
          Start a new search
        </Link>
        .
      </p>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="rounded-xl border border-pink-200 bg-pink-50 px-3 py-2 text-sm text-pink-900">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <LoadingBlock message="Loading your findings…" minHeight="min-h-[40vh]" />
      </div>
    );
  }

  const report = data.analysis_report;
  const allFindings = data.findings ?? [];
  const statisticalCount = allFindings.filter((f) => f.type !== "descriptive").length;
  const hasDescriptiveOnly = allFindings.length > 0 && statisticalCount === 0;
  const visible = showAll ? allFindings : top;
  const hiddenCount = rest.length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      {/* 1. Key findings (AI summary) */}
      <section className="rounded-xl border border-[#e8ddd0] bg-[#faf8f5] p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-pink-700">Key findings</h2>
          {data.ai_summary_source === "anthropic" && (
            <span className="rounded-full bg-pink-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-pink-800">
              AI-generated
            </span>
          )}
          {data.ai_summary_source === "template" && (
            <span className="rounded-full bg-stone-200 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-600">
              Auto summary
            </span>
          )}
        </div>
        <KeyFindingsContent blocks={summaryBlocks} />
        <p className="mt-3 text-xs text-stone-500">
          Interpretive summary from your top results. Detailed result cards below are authoritative.
        </p>
      </section>

      {/* 2. Analysis report (dataset facts) */}
      {report && (
        <section className="mt-6 rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-stone-800">Analysis report</h2>
          <p className="mt-1 text-xs text-stone-500">Factual details about the data analyzed.</p>
          <DatasetDetailsPanel datasets={report.datasets} glossary={data.column_glossary ?? []} />
          {report.notes.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-stone-600">
              {report.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* 3. Key results (computed cards) */}
      <section className="mt-8 rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm" id="key-results">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold text-stone-800">Key results</h2>
          {!showAll && hiddenCount > 0 && (
            <button
              type="button"
              onClick={() => setShowAll(true)}
              className="text-xs font-medium text-pink-600 hover:text-pink-700"
            >
              View all {allFindings.length} results →
            </button>
          )}
          {showAll && hiddenCount > 0 && (
            <button
              type="button"
              onClick={() => setShowAll(false)}
              className="text-xs font-medium text-pink-600 hover:text-pink-700"
            >
              Show top {top.length} only
            </button>
          )}
        </div>

        {data.message && <p className="mt-2 text-sm text-stone-600">{data.message}</p>}

        {allFindings.length === 0 ? (
          <div className="mt-4 rounded-lg border border-[#f0e8de] bg-[#faf8f5] p-4">
            <p className="text-sm font-medium text-stone-700">No significant findings</p>
            <p className="mt-1 text-xs text-stone-500">
              Try NEH grant CSVs on data.gov, or World Bank indicators like Population or GDP.
            </p>
          </div>
        ) : (
          <>
            {hasDescriptiveOnly && (
              <p className="mt-2 text-xs text-amber-800">
                No tests met significance thresholds. Showing descriptive summaries instead.
              </p>
            )}
            {!showAll && hiddenCount > 0 && (
              <p className="mt-2 text-xs text-stone-500">
                Ranked by strength of evidence and effect size; limited to a mix of test types.
              </p>
            )}
            <div className="mt-4">
              <MetricsGuide />
            </div>
            <div className="mt-4 space-y-4">
              {visible.map((finding, index) => (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  compact={showAll}
                  rank={index + 1}
                />
              ))}
            </div>
          </>
        )}
      </section>

      {data.charts.length > 0 && (
        <section className="mt-8 rounded-xl border border-[#e8ddd0] bg-white p-5">
          <h2 className="text-sm font-semibold text-stone-800">Charts</h2>
          <p className="mt-2 text-xs text-stone-500">
            {data.charts.length} chart spec(s) ready — interactive Vega-Lite rendering ships in slice 6.
          </p>
        </section>
      )}

      <section className="mt-8 rounded-xl border border-[#e8ddd0] bg-white p-5">
        <h2 className="text-sm font-semibold text-stone-800">Chat</h2>
        <p className="mt-2 text-sm text-stone-600">Ask questions about these results — slice 8.</p>
      </section>

      <footer className="mt-8 border-t border-[#e8ddd0] pt-4 text-xs text-stone-400">
        <p>Session {sessionId}</p>
        <Link href="/search" className="mt-2 inline-block font-medium text-pink-600 hover:text-pink-700">
          ← New search
        </Link>
      </footer>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<LoadingBlock message="Loading results…" minHeight="min-h-[50vh]" />}>
      <ResultsContent />
    </Suspense>
  );
}
