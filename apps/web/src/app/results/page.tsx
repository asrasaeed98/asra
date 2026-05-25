"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

function ResultsContent() {
  const params = useSearchParams();
  const session = params.get("session") ?? "unknown";

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <p className="text-xs text-zinc-500">Session {session}</p>
      <section className="mt-4 rounded-xl border border-violet-200 bg-violet-50 p-4">
        <h2 className="text-sm font-semibold text-violet-900">
          Executive summary (AI-generated)
        </h2>
        <p className="mt-2 text-sm text-violet-800">
          Placeholder — Anthropic summary runs in finalize (slice 7). Numbers below
          are authoritative.
        </p>
      </section>
      <section className="mt-8">
        <h2 className="text-lg font-semibold">Key results (computed)</h2>
        <div className="mt-4 rounded-xl border border-zinc-200 bg-white p-4">
          <p className="text-sm font-medium">No findings yet</p>
          <p className="mt-1 text-xs text-zinc-500">
            Connect analysis engine (slices 4–6) to populate Finding cards and charts.
          </p>
        </div>
      </section>
      <section className="mt-8 rounded-xl border border-zinc-200 bg-white p-4">
        <h2 className="text-sm font-semibold">Chat</h2>
        <p className="mt-2 text-sm text-zinc-600">
          Grounded chat with SQL citations — slice 8.
        </p>
      </section>
      <Link href="/search" className="mt-8 inline-block text-sm text-emerald-700">
        ← New search
      </Link>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<p className="p-10 text-sm">Loading…</p>}>
      <ResultsContent />
    </Suspense>
  );
}
