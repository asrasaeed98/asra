"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  getGuidedTopics,
  getSearchTopics,
  searchDatasets,
  triggerCatalogSync,
  type CatalogResult,
  type SearchResponse,
  type SearchTopic,
} from "@/lib/api";
import { LoadingBlock } from "@/components/LoadingBlock";
import { formatRowCount, portalBadgeClass, portalLabel } from "@/lib/catalog-labels";

function topicTitle(topics: SearchTopic[], id: string) {
  return topics.find((t) => t.id === id)?.title ?? id.replace(/-/g, " ");
}

function isBrowseLanding(query: string, theme: string, source: string) {
  return !query.trim() && !theme && !source;
}

function TopicBrowseGrid({
  topics,
  topicsLoading,
  onSelectTopic,
}: {
  topics: SearchTopic[];
  topicsLoading: boolean;
  onSelectTopic: (topicId: string) => void;
}) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-stone-800">Browse by theme</h2>
      <p className="mt-1 text-sm text-stone-500">
        Pick a topic to explore datasets, or search by keyword above.
      </p>
      {topicsLoading ? (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              aria-hidden
              className="h-[7.25rem] animate-pulse rounded-2xl border border-[#e8ddd0] bg-[#faf6f0]"
            />
          ))}
        </div>
      ) : (
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {topics.map((t) => (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => onSelectTopic(t.id)}
                className="flex h-full w-full flex-col rounded-2xl border border-[#e8ddd0] bg-white p-4 text-left shadow-sm transition hover:border-pink-200 hover:shadow-md"
              >
                <span className="text-sm font-semibold text-stone-800">{t.title}</span>
                <span className="mt-1 line-clamp-2 text-xs text-stone-500">{t.description}</span>
                <span className="mt-3 text-xs font-medium text-pink-600">
                  {t.dataset_count.toLocaleString()} dataset{t.dataset_count === 1 ? "" : "s"}
                  {t.path_count > 0 &&
                    ` · ${t.path_count} curated example${t.path_count === 1 ? "" : "s"}`}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CityBrowseGrid({
  nycDatasetCount,
  nycLoading,
  onSelectNyc,
}: {
  nycDatasetCount: number | null;
  nycLoading: boolean;
  onSelectNyc: () => void;
}) {
  return (
    <section className="mt-10">
      <h2 className="text-lg font-semibold text-stone-800">Browse by city</h2>
      <p className="mt-1 text-sm text-stone-500">
        Local open-data portals with city-specific datasets.
      </p>
      <ul className="mt-5 grid gap-3 sm:grid-cols-2">
        <li>
          <button
            type="button"
            onClick={onSelectNyc}
            className="flex h-full w-full flex-col rounded-2xl border border-sky-200 bg-gradient-to-br from-sky-50 to-white p-4 text-left shadow-sm transition hover:border-sky-300 hover:shadow-md"
          >
            <span className="text-sm font-semibold text-stone-800">New York City</span>
            <span className="mt-1 line-clamp-2 text-xs text-stone-500">
              NYC Open Data — 311, crime, housing, restaurants, traffic, and more.
            </span>
            <span className="mt-3 text-xs font-medium text-sky-700">
              {nycLoading
                ? "Loading…"
                : nycDatasetCount != null
                  ? `${nycDatasetCount.toLocaleString()} dataset${nycDatasetCount === 1 ? "" : "s"}`
                  : "Browse NYC →"}
            </span>
          </button>
        </li>
      </ul>
    </section>
  );
}

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
  const rowLabel = formatRowCount(item.row_count_hint);
  const addDisabled = !selected && selectionFull;

  return (
    <li className="rounded-xl border border-[#e8ddd0] bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-stone-800">{item.title}</h3>
          {item.organization && (
            <p className="mt-1 text-sm text-stone-600">{item.organization}</p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-stone-500">
            <span className={`rounded-full border px-2 py-0.5 font-medium ${portalBadgeClass(item.portal)}`}>
              {portalLabel(item.portal)}
            </span>
            {rowLabel && (
              <span className="rounded-full border border-emerald-100 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800">
                {rowLabel}
              </span>
            )}
            <span>{licenseDisplay}</span>
          </div>
          {item.attribution_required && (
            <p className="mt-2 rounded-lg border border-pink-100 bg-pink-50/60 px-2 py-1 text-xs text-pink-900">
              Attribution required when sharing results
            </p>
          )}
          {item.match_reason && (
            <p className="mt-2 text-xs text-stone-500">{item.match_reason}</p>
          )}
          {(item.quality_score != null && item.quality_score >= 0.5) && (
            <p className="mt-1 text-xs font-medium text-emerald-700">
              High-quality match for analysis
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
          className={`w-full shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto sm:py-1.5 ${
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
  const [portal, setPortal] = useState(() => params.get("portal") ?? "");
  const [topic, setTopic] = useState(() => params.get("topic") ?? "");
  const [topics, setTopics] = useState<SearchTopic[]>([]);
  const [topicsLoading, setTopicsLoading] = useState(true);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>(() =>
    (params.get("ids") ?? "").split(",").filter(Boolean).slice(0, 2),
  );
  const [nycCount, setNycCount] = useState<number | null>(null);
  const [nycCountLoading, setNycCountLoading] = useState(false);
  const idsFromUrl = params.get("ids") ?? "";

  useEffect(() => {
    setTopicsLoading(true);
    void getSearchTopics()
      .catch(async () => {
        const guided = await getGuidedTopics().catch(() => []);
        return guided.map((t) => ({
          ...t,
          dataset_count: 0,
          path_count: t.path_count,
        }));
      })
      .then(setTopics)
      .finally(() => setTopicsLoading(false));
  }, []);

  useEffect(() => {
    setSelected(idsFromUrl.split(",").filter(Boolean).slice(0, 2));
  }, [idsFromUrl]);

  function updateSearchUrl(patch: { portal?: string; topic?: string; ids?: string[] }) {
    const urlParams = new URLSearchParams(params.toString());
    if ("portal" in patch) {
      if (patch.portal) urlParams.set("portal", patch.portal);
      else urlParams.delete("portal");
    }
    if ("topic" in patch) {
      if (patch.topic) urlParams.set("topic", patch.topic);
      else urlParams.delete("topic");
    }
    if ("ids" in patch) {
      if (patch.ids?.length) urlParams.set("ids", patch.ids.join(","));
      else urlParams.delete("ids");
    }
    const qs = urlParams.toString();
    router.replace(qs ? `/search?${qs}` : "/search", { scroll: false });
  }

  async function runSearch(query = q, source = portal, theme = topic) {
    setLoading(true);
    setError(null);
    try {
      const res = await searchDatasets(query, source || undefined, 1, theme || undefined);
      setData(res);
      if (res.total === 0) {
        const filters: string[] = [];
        if (theme) filters.push(topicTitle(topics, theme));
        if (source) filters.push(portalLabel(source));
        const filterLabel = filters.length ? filters.join(" · ") : "the catalog";
        setError(
          query.trim()
            ? `No datasets match "${query}" in ${filterLabel}. Try another term or filter.`
            : `No datasets in ${filterLabel}. Try another theme or source.`,
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

  function onPortalChange(nextPortal: string) {
    setPortal(nextPortal);
    updateSearchUrl({ portal: nextPortal, topic, ids: selected });
  }

  function onTopicChange(nextTopic: string) {
    setTopic(nextTopic);
    updateSearchUrl({ portal, topic: nextTopic, ids: selected });
  }

  function onSelectNyc() {
    setTopic("");
    setPortal("nyc_open_data");
    updateSearchUrl({ portal: "nyc_open_data", topic: "", ids: selected });
  }

  useEffect(() => {
    if (isBrowseLanding(q, topic, portal)) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    void runSearch(q, portal, topic);
    // Re-search when filters change; q updates go through form submit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [portal, topic]);

  const showTopicBrowse = isBrowseLanding(q, topic, portal);

  useEffect(() => {
    if (!showTopicBrowse) return;
    setNycCountLoading(true);
    void searchDatasets("", "nyc_open_data")
      .then((res) => setNycCount(res.total))
      .catch(() => setNycCount(null))
      .finally(() => setNycCountLoading(false));
  }, [showTopicBrowse]);

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
    let next: string[];
    if (selected.includes(id)) next = selected.filter((x) => x !== id);
    else if (selected.length >= 2) return;
    else next = [...selected, id];
    setSelected(next);
    updateSearchUrl({ portal, topic, ids: next });
  }

  function resetSelection() {
    setSelected([]);
    updateSearchUrl({ portal, topic, ids: [] });
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:py-10">
      <h1 className="text-xl font-semibold text-stone-800 sm:text-2xl">Search datasets</h1>
      <p className="mt-1 text-sm text-stone-600">
        Browse by theme or keyword. Results rank by match quality — best fits first.{" "}
        <Link href="/explore" className="font-medium text-pink-600 hover:text-pink-700">
          Not sure? Try guided explore
        </Link>
      </p>
      <form onSubmit={onSearch} className="mt-6 space-y-3">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. GDP, unemployment, population"
          className="w-full rounded-xl border border-[#ddd0c0] bg-white px-3 py-2.5 text-sm text-stone-800 focus:border-pink-300 focus:outline-none focus:ring-2 focus:ring-pink-100"
        />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-[10px] font-medium uppercase tracking-wide text-stone-400">
              Theme
            </span>
            <select
              value={topic}
              onChange={(e) => onTopicChange(e.target.value)}
              className="rounded-xl border border-[#ddd0c0] bg-white px-3 py-2.5 text-sm text-stone-700 focus:border-pink-300 focus:outline-none focus:ring-2 focus:ring-pink-100"
            >
              <option value="">All themes</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-1 flex-col gap-1">
            <span className="text-[10px] font-medium uppercase tracking-wide text-stone-400">
              Source
            </span>
            <select
              value={portal}
              onChange={(e) => onPortalChange(e.target.value)}
              className="rounded-xl border border-[#ddd0c0] bg-white px-3 py-2.5 text-sm text-stone-700 focus:border-pink-300 focus:outline-none focus:ring-2 focus:ring-pink-100"
            >
              <option value="">All sources</option>
              <option value="data_gov">data.gov only</option>
              <option value="world_bank">World Bank only</option>
              <option value="fred">FRED only</option>
              <option value="nyc_open_data">NYC Open Data only</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-pink-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-pink-200/50 transition hover:bg-pink-700 disabled:opacity-50 sm:mb-0"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      {loading && !data && !showTopicBrowse && (
        <div className="mt-8">
          <LoadingBlock message="Searching the catalog…" />
        </div>
      )}

      {showTopicBrowse && (
        <>
          <TopicBrowseGrid
            topics={topics}
            topicsLoading={topicsLoading}
            onSelectTopic={onTopicChange}
          />
          <CityBrowseGrid
            nycDatasetCount={nycCount}
            nycLoading={nycCountLoading}
            onSelectNyc={onSelectNyc}
          />
        </>
      )}

      {error && !showTopicBrowse && (
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

      {data && !showTopicBrowse && (
        <>
          {loading && (
            <p className="mt-4 text-xs text-stone-500">Updating results…</p>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1">
            <p className="text-sm text-stone-500">
              Selected: {selected.length} / 2
              {data && ` · ${data.total} result(s)`}
              {topic ? ` · ${topicTitle(topics, topic)}` : ""}
              {portal ? ` · ${portalLabel(portal)} only` : ""}
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
