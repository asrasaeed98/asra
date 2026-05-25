"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { LoadingBlock } from "@/components/LoadingBlock";

function ResultsContent() {
  const params = useSearchParams();
  const session = params.get("session") ?? "unknown";
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 1200);
    return () => clearTimeout(t);
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <LoadingBlock message="Loading your findings…" minHeight="min-h-[40vh]" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <p className="text-xs text-stone-400">Session {session}</p>
      <section className="mt-4 rounded-xl border border-[#e8ddd0] bg-[#faf8f5] p-5">
        <h2 className="text-sm font-semibold text-pink-700">Executive summary (AI-generated)</h2>
        <p className="mt-2 text-sm text-stone-600">
          Placeholder — Anthropic summary runs in finalize (slice 7). Numbers in the cards
          below are authoritative.
        </p>
      </section>
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-stone-800">Key results (computed)</h2>
        <div className="mt-4 rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-stone-700">No findings yet</p>
          <p className="mt-1 text-xs text-stone-500">
            Analysis engine (slices 4–6) will populate cards and charts here.
          </p>
        </div>
      </section>
      <section className="mt-8 rounded-xl border border-[#e8ddd0] bg-white p-5">
        <h2 className="text-sm font-semibold text-stone-800">Chat</h2>
        <p className="mt-2 text-sm text-stone-600">Grounded chat — slice 8.</p>
      </section>
      <Link
        href="/search"
        className="mt-8 inline-block text-sm font-medium text-pink-600 hover:text-pink-700"
      >
        ← New search
      </Link>
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
