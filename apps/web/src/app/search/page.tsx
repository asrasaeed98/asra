"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";
import {
  getApiHealth,
  searchDatasets,
  triggerCatalogSync,
  type CatalogResult,
  type SearchResponse,
} from "@/lib/api";
import { LoadingBlock } from "@/components/LoadingBlock";

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
    <li className="rounded-xl border border-[#e8ddd0] bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
            {portalLabel} · {item.format ?? "data"}
          </p>
          <h3 className="mt-1 font-medium text-stone-800">{item.title}</h3>
          {item.organization && (
            <p className="mt-1 text-sm text-stone-600">{item.organization}</p>
          )}
          <p className="mt-2 text-xs text-stone-500">{item.license_display}</p>
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
          className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
            selected
              ? "border border-[#e8ddd0] bg-[#f5efe6] text-stone-700"
              : "bg-pink-600 text-white hover:bg-pink-700"
          }`}
        >
          {selected ? "Remove" : "Add"}
        </button>
      </div>
      <p className="mt-3 border-t border-[#f5efe6] pt-2 text-xs text-stone-400">
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
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [catalogCount, setCatalogCount] = useState<number | null>(null);
  const [selected, setSelected] = useState<string[]>([]);

  const runSearch = useCallback(async (query: string, portalFilter?: string) => {
    setLoading(true);
    setError(null);
    try {
      const health = await getApiHealth();
      setApiOk(true);
      setCatalogCount(health.catalog_count);

      const res = await searchDatasets(query, portalFilter || undefined);
      setData(res);
      if (res.total === 0) {
        if (health.catalog_count === 0) {
          setError(
            "Catalog is empty. Click “Load catalog” below (API must be running on port 8000).",
          );
        } else {
          setError("No datasets match that search. Try a broader term like gdp, health, or population.");
        }
      }
    } catch {
      setApiOk(false);
      setError(
        "Could not reach the API. In a second terminal, from the project folder run: uvicorn findings_api.main:app --reload --port 8000",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    runSearch("");
  }, [runSearch]);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    await runSearch(q, portal || undefined);
  }

  async function onSyncCatalog() {
    setSyncing(true);
    setError(null);
    try {
      const result = await triggerCatalogSync();
      setCatalogCount(Object.values(result.indexed).reduce((a, b) => a + b, 0));
      await runSearch(q, portal || undefined);
    } catch {
      setError("Catalog sync failed. Is the API running on http://localhost:8000 ?");
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

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-stone-800">Search open datasets</h1>
      <p className="mt-1 text-sm text-stone-600">
        {APP_NAME} — pick up to 2. Sources show license and attribution up front.
      </p>
      {apiOk && catalogCount != null && catalogCount > 0 && (
        <p className="mt-2 text-xs text-stone-500">
          {catalogCount} datasets in catalog · API connected
        </p>
      )}

      <form onSubmit={onSearch} className="mt-6 flex flex-col gap-3 sm:flex-row">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. GDP, unemployment, population (empty = browse all)"
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

      {(catalogCount === 0 || apiOk === false) && (
        <div className="mt-4 rounded-xl border border-[#e8ddd0] bg-[#f5efe6] p-4 text-sm text-stone-700">
          <p className="font-medium text-stone-800">First-time setup</p>
          <ol className="mt-2 list-inside list-decimal space-y-1 text-stone-600">
            <li>
              Start the API:{" "}
              <code className="text-xs">uvicorn findings_api.main:app --reload --port 8000</code>
            </li>
            <li>Load datasets into the local catalog (once per machine):</li>
          </ol>
          <button
            type="button"
            onClick={onSyncCatalog}
            disabled={syncing}
            className="mt-3 rounded-lg bg-pink-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:bg-pink-700"
          >
            {syncing ? "Loading catalog…" : "Load catalog"}
          </button>
        </div>
      )}

      {loading && (
        <div className="mt-8">
          <LoadingBlock message="Searching the catalog…" />
        </div>
      )}

      {error && !loading && (
        <p className="mt-4 rounded-xl border border-[#e8ddd0] bg-[#f5efe6] px-3 py-2 text-sm text-stone-700">
          {error}
        </p>
      )}

      {!loading && (
        <>
          <p className="mt-4 text-sm text-stone-500">
            Selected: {selected.length} / 2
            {data && ` · ${data.total} result(s)`}
          </p>
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
                onToggle={() => toggle(item.id)}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
