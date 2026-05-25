"use client";

import { useState } from "react";
import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";
import { searchDatasets, type CatalogResult, type SearchResponse } from "@/lib/api";

function ResultCard({
  item,
  selected,
  onToggle,
}: {
  item: CatalogResult;
  selected: boolean;
  onToggle: () => void;
}) {
  const portalLabel = item.portal === "world_bank" ? "World Bank" : "data.gov";
  return (
    <li className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            {portalLabel} · {item.format ?? "data"}
          </p>
          <h3 className="mt-1 font-medium text-zinc-900">{item.title}</h3>
          {item.organization && (
            <p className="mt-1 text-sm text-zinc-600">{item.organization}</p>
          )}
          <p className="mt-2 text-xs text-zinc-500">{item.license_display}</p>
          {item.attribution_required && (
            <p className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">
              Attribution required when sharing results
            </p>
          )}
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-xs text-emerald-700 hover:underline"
          >
            View original source →
          </a>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium ${
            selected
              ? "bg-zinc-200 text-zinc-800"
              : "bg-emerald-700 text-white hover:bg-emerald-800"
          }`}
        >
          {selected ? "Remove" : "Add"}
        </button>
      </div>
      <p className="mt-3 border-t border-zinc-100 pt-2 text-xs text-zinc-400">
        {item.attribution_text}
      </p>
    </li>
  );
}

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [portal, setPortal] = useState<string>("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await searchDatasets(q, portal || undefined);
      setData(res);
      if (res.total === 0) {
        setError(
          "No datasets found. Run catalog sync: POST /admin/sync on the API (once per environment).",
        );
      }
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
        {APP_NAME} — license-safe catalog from data.gov (CC0/PD) and World Bank (CC
        BY, attribution shown). Select up to 2.
      </p>
      <form onSubmit={onSearch} className="mt-6 flex flex-col gap-3 sm:flex-row">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. GDP, unemployment, population"
          className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
        />
        <select
          value={portal}
          onChange={(e) => setPortal(e.target.value)}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
        >
          <option value="">All sources</option>
          <option value="data_gov">data.gov only</option>
          <option value="world_bank">World Bank only</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {error && (
        <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {error}
        </p>
      )}
      <p className="mt-4 text-sm text-zinc-500">
        Selected: {selected.length} / 2
        {data && ` · ${data.total} result(s)`}
      </p>
      {selected.length > 0 && (
        <Link
          href={`/review?ids=${selected.join(",")}`}
          className="mt-4 inline-block rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white"
        >
          Review & analyze
        </Link>
      )}
      <ul className="mt-6 space-y-4">
        {data?.results?.map((item) => (
          <ResultCard
            key={item.id}
            item={item}
            selected={selected.includes(item.id)}
            onToggle={() => toggle(item.id)}
          />
        ))}
      </ul>
    </div>
  );
}
