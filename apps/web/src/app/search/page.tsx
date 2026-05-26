"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  searchDatasets,
  triggerCatalogSync,
  type CatalogResult,
  type SearchResponse,
} from "@/lib/api";
import { LoadingBlock } from "@/components/LoadingBlock";

function ResultCard({
  item,
  selected,
  selectionFull,
  onToggle,
}: {
  item: CatalogResult;
  selected: boolean;
  selectionFull: boolean;
  onToggle: () => void;
}) {
  const licenseDisplay = item.license_display
    .replace(/\s*[—–-]\s*attribution required/i, "")
    .trim();
  const addDisabled = !selected && selectionFull;

  return (
    <li className="rounded-xl border border-[#e8ddd0] bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-stone-800">{item.title}</h3>
          {item.organization && (
            <p className="mt-1 text-sm text-stone-600">{item.organization}</p>
          )}
          <p className="mt-2 text-xs text-stone-500">{licenseDisplay}</p>
          {item.attribution_required && (
            <p className="mt-2 rounded-lg border border-pink-100 bg-pink-50/60 px-2 py-1 text-xs text-pink-900">
              Attribution required when sharing results
            </p>
          )}
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-xs font-medium text-pink-600 hover:text-pink-700"
          >
            View original source →
          </a>
        </div>
        <button
          type="button"
          onClick={onToggle}
          disabled={addDisabled}
          className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
            selected
              ? "border border-[#e8ddd0] bg-[#f5efe6] text-stone-700"
              : addDisabled
                ? "bg-stone-300 text-stone-500"
                : "bg-pink-600 text-white hover:bg-pink-700"
          }`}
        >
          {selected ? "Remove" : "Add"}
        </button>
      </div>
    </li>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<LoadingBlock message="Loading search…" minHeight="min-h-[40vh]" />}>
      <SearchContent />
    </Suspense>
  );
}

function SearchContent() {
  const params = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [portal, setPortal] = useState<string>("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    const fromUrl = (params.get("ids") ?? "").split(",").filter(Boolean).slice(0, 2);
    setSelected(fromUrl);
  }, [params]);

  async function runSearch(query = q, source = portal) {
    setLoading(true);
    setError(null);
    try {
      const res = await searchDatasets(query, source || undefined);
      setData(res);
      if (res.total === 0) {
        setError(
          query.trim()
            ? "No datasets match that search. Try another term or load the catalog."
            : "Catalog is empty. Load datasets from data.gov and World Bank (once per environment).",
        );
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not reach API. Start the API on port 8000.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    await runSearch();
  }

  useEffect(() => {
    void runSearch("");
  }, []);

  async function onLoadCatalog() {
    setSyncing(true);
    setError(null);
    try {
      const res = await triggerCatalogSync();
      const total = Object.values(res.indexed).reduce((a, b) => a + b, 0);
      await runSearch();
      if (total === 0) {
        setError("Sync finished but no license-safe datasets were indexed.");
      }
    } catch {
      setError("Could not sync catalog. Make sure the API is running on port 8000.");
    } finally {
      setSyncing(false);
    }
  }

  function toggle(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return prev;
      return [...prev, id];
    });
  }

  function resetSelection() {
    setSelected([]);
    router.replace("/search");
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-stone-800">Search datasets</h1>
      <p className="mt-1 text-sm text-stone-600">
        Sources show license and attribution. Pick up to 2.
      </p>
      <form onSubmit={onSearch} className="mt-6 flex flex-col gap-3 sm:flex-row">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. GDP, unemployment, population"
          className="flex-1 rounded-xl border border-[#ddd0c0] bg-white px-3 py-2.5 text-sm text-stone-800 focus:border-pink-300 focus:outline-none focus:ring-2 focus:ring-pink-100"
        />
        <select
          value={portal}
          onChange={(e) => setPortal(e.target.value)}
          className="rounded-xl border border-[#ddd0c0] bg-white px-3 py-2.5 text-sm text-stone-700"
        >
          <option value="">All sources</option>
          <option value="data_gov">data.gov only</option>
          <option value="world_bank">World Bank only</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50 hover:bg-pink-700"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {loading && !data && (
        <div className="mt-8">
          <LoadingBlock message="Searching the catalog…" />
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-xl border border-[#e8ddd0] bg-[#f5efe6] px-3 py-2 text-sm text-stone-700">
          <p>{error}</p>
          {(data?.total === 0 || !data) && (
            <button
              type="button"
              onClick={onLoadCatalog}
              disabled={syncing}
              className="mt-2 rounded-lg bg-pink-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50 hover:bg-pink-700"
            >
              {syncing ? "Loading catalog…" : "Load catalog"}
            </button>
          )}
        </div>
      )}

      {data && (
        <>
          {loading && (
            <p className="mt-4 text-xs text-stone-500">Updating results…</p>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1">
            <p className="text-sm text-stone-500">
              Selected: {selected.length} / 2
              {data && ` · ${data.total} result(s)`}
            </p>
            {selected.length > 0 && (
              <button
                type="button"
                onClick={resetSelection}
                className="text-sm font-medium text-pink-600 hover:text-pink-700"
              >
                Reset selection
              </button>
            )}
          </div>
          {selected.length > 0 && (
            <Link
              href={`/review?ids=${selected.join(",")}`}
              className="mt-4 inline-block rounded-xl bg-pink-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-pink-700"
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
                selectionFull={selected.length >= 2}
                onToggle={() => toggle(item.id)}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
