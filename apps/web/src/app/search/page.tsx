"use client";

import { useState } from "react";
import Link from "next/link";
import { searchDatasets, type SearchResponse } from "@/lib/api";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await searchDatasets(q);
      setData(res);
    } catch {
      setError("Could not reach API. Start the API on port 8000.");
    } finally {
      setLoading(false);
    }
  }

  function toggle(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return prev;
      return [...prev, id];
    });
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold">Search open datasets</h1>
      <p className="mt-1 text-sm text-zinc-600">
        Select up to 2 datasets. Catalog sync coming in slice 2.
      </p>
      <form onSubmit={onSearch} className="mt-6 flex gap-2">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. unemployment by state"
          className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {data?.message && (
        <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {data.message}
        </p>
      )}
      <p className="mt-4 text-sm text-zinc-500">Selected: {selected.length} / 2</p>
      {selected.length > 0 && (
        <Link
          href={`/review?ids=${selected.join(",")}`}
          className="mt-4 inline-block rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white"
        >
          Review & analyze
        </Link>
      )}
      <ul className="mt-6 space-y-2">
        {data?.results?.map((item: unknown) => {
          const r = item as { id?: string; title?: string };
          const id = r.id ?? "unknown";
          return (
            <li
              key={id}
              className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3"
            >
              <span className="text-sm">{r.title ?? id}</span>
              <button
                type="button"
                onClick={() => toggle(id)}
                className="text-sm text-emerald-700"
              >
                {selected.includes(id) ? "Remove" : "Add"}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
