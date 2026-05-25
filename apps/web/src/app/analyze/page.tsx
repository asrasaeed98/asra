"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FunFindsLoader } from "@/components/FunFindsLoader";
import { LoadingBlock } from "@/components/LoadingBlock";

const PHASES = [
  { id: "ingest", label: "Loading your data" },
  { id: "prepare", label: "Preparing table" },
  { id: "join", label: "Combining datasets" },
  { id: "analyze", label: "Running analysis" },
  { id: "finalize", label: "Building results & summary" },
];

function AnalyzeContent() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = params.get("ids") ?? "";
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [phaseMessage, setPhaseMessage] = useState(PHASES[0].label);

  useEffect(() => {
    if (!ids) return;
    const t = setInterval(() => {
      setPhaseIndex((i) => {
        if (i >= PHASES.length - 1) {
          clearInterval(t);
          setTimeout(() => router.push(`/results?session=demo`), 800);
          return i;
        }
        const next = i + 1;
        setPhaseMessage(PHASES[next].label);
        return next;
      });
    }, 1200);
    return () => clearInterval(t);
  }, [ids, router]);

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <div className="mb-8 flex justify-center">
        <FunFindsLoader message={phaseMessage} size="lg" />
      </div>
      <h1 className="text-center text-xl font-semibold text-slate-800">Analysis in progress</h1>
      <p className="mt-1 text-center text-sm text-slate-500">Usually 2–4 minutes</p>
      <ol className="mt-8 space-y-3 rounded-xl border border-pink-100 bg-white p-4">
        {PHASES.map((p, i) => (
          <li key={p.id} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                i < phaseIndex
                  ? "bg-pink-500 text-white"
                  : i === phaseIndex
                    ? "bg-pink-600 text-white ring-2 ring-pink-200"
                    : "bg-pink-50 text-pink-300"
              }`}
            >
              {i < phaseIndex ? "✓" : i + 1}
            </span>
            <span className={i <= phaseIndex ? "text-slate-800" : "text-slate-400"}>
              {p.label}
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-center text-xs text-slate-400">
        Demo progress — real worker wiring in slice 5.
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
