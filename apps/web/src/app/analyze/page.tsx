"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

const PHASES = [
  { id: "ingest", label: "Loading your data" },
  { id: "prepare", label: "Preparing table" },
  { id: "join", label: "Combining datasets" },
  { id: "analyze", label: "Running analysis" },
  { id: "finalize", label: "Building results" },
];

function AnalyzeContent() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = params.get("ids") ?? "";
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    if (!ids) return;
    const t = setInterval(() => {
      setPhaseIndex((i) => {
        if (i >= PHASES.length - 1) {
          clearInterval(t);
          setTimeout(() => router.push(`/results?session=demo`), 800);
          return i;
        }
        return i + 1;
      });
    }, 1200);
    return () => clearInterval(t);
  }, [ids, router]);

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <h1 className="text-2xl font-semibold">Analysis in progress</h1>
      <p className="mt-1 text-sm text-zinc-600">Usually 2–4 minutes</p>
      <ol className="mt-8 space-y-4">
        {PHASES.map((p, i) => (
          <li key={p.id} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                i < phaseIndex
                  ? "bg-emerald-600 text-white"
                  : i === phaseIndex
                    ? "bg-zinc-900 text-white"
                    : "bg-zinc-200 text-zinc-500"
              }`}
            >
              {i < phaseIndex ? "✓" : i + 1}
            </span>
            <span className={i <= phaseIndex ? "text-zinc-900" : "text-zinc-400"}>
              {p.label}
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-8 text-xs text-zinc-500">
        Demo progress UI — worker integration in slice 5.
      </p>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<p className="p-10 text-sm">Loading…</p>}>
      <AnalyzeContent />
    </Suspense>
  );
}
