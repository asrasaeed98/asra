"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FunFindsLoader } from "@/components/FunFindsLoader";
import { formatSeconds, LoadingBlock } from "@/components/LoadingBlock";
import { getSessionStatus, type SessionStatus } from "@/lib/api";

const PHASES = [
  { id: "ingest", label: "Loading your data" },
  { id: "prepare", label: "Preparing table" },
  { id: "join", label: "Combining datasets" },
  { id: "analyze", label: "Running analysis" },
  { id: "finalize", label: "Building results & summary" },
];

function phaseIndexFromStatus(status: SessionStatus): number {
  if (status.status === "complete") return 4;
  const map: Record<string, number> = {
    pending: 0,
    ingest: 0,
    ready: 1,
    prepare: 1,
    join: 2,
    analyze: 3,
    finalize: 4,
  };
  return map[status.phase] ?? 0;
}

function AnalyzeContent() {
  const params = useSearchParams();
  const router = useRouter();
  const sessionId = params.get("session") ?? "";
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [phaseMessage, setPhaseMessage] = useState(PHASES[0].label);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    async function poll() {
      try {
        const s = await getSessionStatus(sessionId);
        if (cancelled) return;
        setStatus(s);
        const idx = phaseIndexFromStatus(s);
        setPhaseIndex(idx);
        setPhaseMessage(s.message ?? PHASES[idx]?.label ?? PHASES[0].label);

        if (s.status === "failed") {
          setError(s.message ?? "Analysis failed");
          return;
        }
        if (s.status === "complete") {
          router.push(`/results?session=${sessionId}`);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not reach API");
      }
    }

    poll();
    const t = setInterval(poll, 1500);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [sessionId, router]);

  if (!sessionId) {
    return (
      <p className="text-center text-sm text-stone-600">
        Missing session.{" "}
        <a href="/search" className="text-pink-600 hover:text-pink-700">
          Start from search
        </a>
        .
      </p>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-4 py-10 text-center">
        <p className="rounded-xl border border-pink-200 bg-pink-50 px-3 py-2 text-sm text-pink-900">
          {error}
        </p>
      </div>
    );
  }

  const timeHint =
    status?.estimate_remaining_sec != null
      ? formatSeconds(status.estimate_remaining_sec)
      : status?.message?.toLowerCase().includes("minute") ||
          status?.message?.toLowerCase().includes("downloaded")
        ? "May take several minutes for large datasets"
        : "Usually 2–4 minutes";

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <div className="mb-8 flex justify-center">
        <FunFindsLoader message={phaseMessage} size="lg" />
      </div>
      <h1 className="text-center text-xl font-semibold text-stone-800">Analysis in progress</h1>
      <p className="mt-1 text-center text-sm text-stone-500">{timeHint}</p>
      {status?.percent != null && status.percent >= 0 && (
        <div className="mx-auto mt-4 w-full max-w-xs">
          <div className="h-2 overflow-hidden rounded-full bg-[#e8ddd0]">
            <div
              className="h-full rounded-full bg-pink-500 transition-all duration-500"
              style={{ width: `${Math.min(100, status.percent)}%` }}
            />
          </div>
          <p className="mt-2 text-center text-xs text-stone-400">{status.percent}% complete</p>
        </div>
      )}
      <ol className="mt-8 space-y-3 rounded-xl border border-[#e8ddd0] bg-white p-4">
        {PHASES.map((p, i) => (
          <li key={p.id} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                i < phaseIndex
                  ? "bg-pink-500 text-white"
                  : i === phaseIndex
                    ? "bg-pink-600 text-white ring-2 ring-pink-200"
                    : "bg-[#f5efe6] text-stone-400"
              }`}
            >
              {i < phaseIndex ? "✓" : i + 1}
            </span>
            <span className={i <= phaseIndex ? "text-stone-800" : "text-stone-400"}>
              {p.label}
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-center text-xs text-stone-400">
        Statistical tests run automatically; a plain-language summary is generated when results are ready.
      </p>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<LoadingBlock message="Starting analysis…" minHeight="min-h-[50vh]" />}>
      <AnalyzeContent />
    </Suspense>
  );
}
