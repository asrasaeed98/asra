"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { LoadingBlock } from "@/components/LoadingBlock";

function ReviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = (params.get("ids") ?? "").split(",").filter(Boolean);
  const [intent, setIntent] = useState("");
  const [ml, setMl] = useState(true);
  const [starting, setStarting] = useState(false);

  if (ids.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        No datasets selected.{" "}
        <a href="/search" className="text-pink-600 hover:underline">
          Go back to search
        </a>
        .
      </p>
    );
  }

  function runAnalysis() {
    setStarting(true);
    router.push(`/analyze?ids=${ids.join(",")}&ml=${ml}`);
  }

  if (starting) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <LoadingBlock message="Getting ready to analyze…" minHeight="min-h-[40vh]" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Review & confirm</h1>
      <p className="mt-1 text-sm text-slate-600">Estimated time: 2–4 minutes</p>
      <ul className="mt-6 space-y-2 rounded-xl border border-pink-100 bg-white p-4 text-sm text-slate-700">
        {ids.map((id) => (
          <li key={id} className="truncate">
            <span className="text-pink-400">✦</span> {id}
          </li>
        ))}
      </ul>
      <label className="mt-6 block text-sm font-medium text-slate-700">
        What are you trying to learn? (optional)
        <input
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="mt-1 w-full rounded-xl border border-pink-200 px-3 py-2 focus:ring-2 focus:ring-pink-200"
          placeholder="e.g. housing vs income by state"
        />
      </label>
      <label className="mt-4 flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={ml}
          onChange={(e) => setMl(e.target.checked)}
          className="accent-pink-600"
        />
        Include ML insights (clustering & anomalies)
      </label>
      <p className="mt-6 text-xs text-slate-500">
        Correlation does not imply causation. Large datasets may use a disclosed random sample.
      </p>
      <button
        type="button"
        onClick={runAnalysis}
        className="mt-8 rounded-xl bg-pink-600 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-pink-100 hover:bg-pink-700"
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
