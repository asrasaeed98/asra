"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function ReviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = (params.get("ids") ?? "").split(",").filter(Boolean);
  const [intent, setIntent] = useState("");
  const [ml, setMl] = useState(true);

  if (ids.length === 0) {
    return (
      <p className="text-sm text-zinc-600">
        No datasets selected. <a href="/search">Go back to search</a>.
      </p>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold">Review & confirm</h1>
      <p className="mt-1 text-sm text-zinc-600">Estimated time: 2–4 minutes</p>
      <ul className="mt-6 list-disc pl-5 text-sm text-zinc-700">
        {ids.map((id) => (
          <li key={id}>{id}</li>
        ))}
      </ul>
      <label className="mt-6 block text-sm font-medium">
        What are you trying to learn? (optional)
        <input
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
          placeholder="e.g. housing vs income by state"
        />
      </label>
      <label className="mt-4 flex items-center gap-2 text-sm">
        <input type="checkbox" checked={ml} onChange={(e) => setMl(e.target.checked)} />
        Include ML insights (clustering & anomalies)
      </label>
      <p className="mt-6 text-xs text-zinc-500">
        We will run statistics on your data. Correlation does not imply causation.
        Large datasets may use a disclosed random sample.
      </p>
      <button
        type="button"
        onClick={() => router.push(`/analyze?ids=${ids.join(",")}&ml=${ml}`)}
        className="mt-8 rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white"
      >
        Run analysis
      </button>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<p className="p-10 text-sm">Loading…</p>}>
      <ReviewContent />
    </Suspense>
  );
}
