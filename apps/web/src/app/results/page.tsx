"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ChatPanel } from "@/components/ChatPanel";
import { DatasetDetailsPanel, FindingCard, MetricsGuide } from "@/components/FindingCard";
import { KeyFindingsContent } from "@/components/KeyFindingsContent";
import { LoadingBlock } from "@/components/LoadingBlock";
import { VegaChart } from "@/components/VegaChart";
import { getSessionResults, type Finding, type SessionResults } from "@/lib/api";
import { formatSummaryBlocks } from "@/lib/summary-format";

function analysisReportSummary(
  report: NonNullable<SessionResults["analysis_report"]>,
): string[] {
  const datasets = report.datasets ?? [];
  const rows = datasets.reduce((sum, d) => sum + (d.n_rows || 0), 0);
  const sig = report.statistical_findings ?? report.total_findings ?? 0;
  const planned = report.tests_planned ?? 0;
  const titles = datasets.map((d) => d.title).filter(Boolean);
  const joined = titles.some((t) => t.includes(" + "));
  const rowsStr = rows.toLocaleString();
  const lines: string[] = [];

  if (planned > 0) {
    const analyses = planned === 1 ? "analysis" : "analyses";
    const patterns =
      sig === 1 ? "1 statistically meaningful pattern" : `${sig} statistically meaningful patterns`;
    lines.push(
      sig > 0
        ? `We ran ${planned} ${analyses} on ${rowsStr} rows and found ${patterns}, shown as the result cards below. Each is unlikely to be due to chance (p < 0.05).`
        : `We ran ${planned} ${analyses} on ${rowsStr} rows but found no statistically significant patterns.`,
    );
  } else if ((report.total_findings ?? 0) > 0) {
    const n = report.total_findings ?? 0;
    lines.push(`We summarized ${rowsStr} rows of data (${n} descriptive result${n === 1 ? "" : "s"}).`);
  }

  if (titles.length) {
    lines.push(
      joined
        ? `Data analyzed: ${titles.join("; ")} — two datasets joined and compared.`
        : `Data analyzed: ${titles.join("; ")}.`,
    );
  }
  return lines;
}

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

function ResultsSkeleton({ message, percent }: { message: string; percent?: number }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-6">
      <section className="rounded-xl border border-[#e8ddd0] bg-[#faf8f5] p-5">
        <h2 className="text-sm font-semibold text-pink-700">Key findings</h2>
        <LoadingBlock message={message} minHeight="min-h-[180px]" percent={percent} />
      </section>
      <section className="rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm animate-pulse">
        <div className="h-4 w-32 rounded bg-[#e8ddd0]" />
        <div className="mt-3 h-3 w-full rounded bg-[#f0e8de]" />
        <div className="mt-2 h-3 w-2/3 rounded bg-[#f0e8de]" />
      </section>
    </div>
  );
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
    const t = setInterval(async () => {
      if (cancelled) return;
      try {
        const res = await getSessionResults(sessionId);
        if (cancelled) return;
        setData(res);
        if (res.status === "complete" || res.status === "failed") {
          clearInterval(t);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load results");
        clearInterval(t);
      }
    }, 1500);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [sessionId]);

  const isComplete = data?.status === "complete";
  const isFailed = data?.status === "failed";
  const loadingMessage =
    data?.message ??
    (data?.phase === "finalize" ? "Writing summary and building results…" : "Finishing analysis…");

  const { top, rest } = useMemo(
    () => (data && isComplete ? resolveDisplayFindings(data) : { top: [], rest: [] }),
    [data, isComplete],
  );
  const summaryBlocks = useMemo(
    () => (isComplete ? formatSummaryBlocks(data?.ai_summary, data?.ai_summary_blocks) : []),
    [data?.ai_summary, data?.ai_summary_blocks, isComplete],
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

  if (error || isFailed) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="rounded-xl border border-pink-200 bg-pink-50 px-3 py-2 text-sm text-pink-900">
          {error ?? data?.message ?? "Analysis failed"}
        </p>
      </div>
    );
  }

  if (!data || !isComplete) {
    return (
      <ResultsSkeleton
        message={loadingMessage}
        percent={data?.percent}
      />
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

      {/* 2. Key results (computed cards + visuals — the evidence) */}
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
              Try a dataset with more rows and multiple numeric columns, or broaden your filters.
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
        <section className="mt-8 rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-stone-800">Charts</h2>
          <p className="mt-1 text-xs text-stone-500">
            Visual summaries linked to key findings ({data.charts.length} chart
            {data.charts.length === 1 ? "" : "s"}).
          </p>
          <div className="mt-4 grid gap-6 lg:grid-cols-2">
            {data.charts.map((chart) => (
              <article
                key={chart.id}
                id={`chart-${chart.finding_id}`}
                className="rounded-lg border border-[#f0e8de] bg-[#faf8f5] p-4"
              >
                <h3 className="text-sm font-medium text-stone-800">{chart.title}</h3>
                <p className="mt-0.5 text-xs capitalize text-stone-500">{chart.type} chart</p>
                <div className="mt-3">
                  <VegaChart spec={chart.spec} title={chart.title} />
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* 3. Grounded chat (after the evidence, so questions are informed) */}
      <ChatPanel sessionId={sessionId} initial={data.chat} />

      {/* 4. Analysis report / technical details (collapsed depth) */}
      {report && (
        <section className="mt-6 rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-stone-800">Analysis report</h2>
          <div className="mt-2 space-y-1.5 text-sm leading-relaxed text-stone-700">
            {analysisReportSummary(report).map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
          <DatasetDetailsPanel
            datasets={report.datasets}
            glossary={data.column_glossary ?? []}
            measureNotes={report.measure_notes ?? []}
          />
          {report.notes.length > 0 && (
            <details className="mt-3 text-xs">
              <summary className="cursor-pointer font-medium text-stone-500 hover:text-stone-700">
                Technical details
              </summary>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 leading-relaxed text-stone-500">
                {report.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

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
