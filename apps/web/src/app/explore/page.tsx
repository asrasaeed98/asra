"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  getGuidedPaths,
  getGuidedTopics,
  guidedSuggest,
  type GuidedPathPair,
  type GuidedSuggestResponse,
  type GuidedTopic,
} from "@/lib/api";
import { LoadingBlock } from "@/components/LoadingBlock";

const EXAMPLE_QUESTIONS = [
  "Do wealthier countries live longer?",
  "Electricity vs clean cooking access",
  "US unemployment over time",
];

function topicLabel(topics: GuidedTopic[], id: string) {
  return topics.find((t) => t.id === id)?.title ?? id.replace(/-/g, " ");
}

function PathCard({
  path,
  topics,
  onUse,
  featured = false,
}: {
  path: GuidedPathPair;
  topics: GuidedTopic[];
  onUse: () => void;
  featured?: boolean;
}) {
  const isPair = path.resource_ids.length > 1;
  const datasetLine = path.datasets.map((d) => d.title.split(",")[0]).join(" + ");

  return (
    <article
      className={`rounded-2xl border bg-white p-4 shadow-sm transition-shadow hover:shadow-md sm:p-5 ${
        featured
          ? "border-violet-300 ring-1 ring-violet-100"
          : "border-[#e8ddd0]"
      }`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-medium uppercase tracking-wide text-stone-400">
              {topicLabel(topics, path.topic)}
            </span>
            {path.quality === "verified" && (
              <span className="rounded-md bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                Verified
              </span>
            )}
          </div>
          <h3 className="mt-1.5 text-base font-semibold leading-snug text-stone-800">
            {path.title}
          </h3>
          <p className="mt-1 line-clamp-2 text-sm text-stone-600">{path.description}</p>
          <p className="mt-2 truncate text-xs text-stone-500" title={datasetLine}>
            {isPair ? "Pair: " : "Dataset: "}
            {datasetLine}
          </p>
        </div>
        <button
          type="button"
          onClick={onUse}
          className={`shrink-0 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
            featured
              ? "bg-violet-600 text-white hover:bg-violet-700"
              : "border border-[#ddd0c0] bg-[#faf8f5] text-stone-800 hover:border-violet-300 hover:text-violet-800"
          }`}
        >
          {isPair ? "Use pair" : "Analyze"}
        </button>
      </div>

      <details className="mt-3 group">
        <summary className="cursor-pointer text-xs font-medium text-stone-400 hover:text-violet-600">
          Why this example
        </summary>
        <p className="mt-2 text-xs leading-relaxed text-stone-500">{path.why}</p>
        <ul className="mt-2 space-y-0.5 text-xs text-stone-500">
          {path.datasets.map((d) => (
            <li key={d.id}>· {d.title}</li>
          ))}
        </ul>
      </details>
    </article>
  );
}

function PairingsSection({
  title,
  paths,
  topics,
  topicFilter,
  onTopicFilter,
  onUse,
  featuredFirst = false,
}: {
  title: string;
  paths: GuidedPathPair[];
  topics: GuidedTopic[];
  topicFilter: string;
  onTopicFilter: (id: string) => void;
  onUse: (path: GuidedPathPair) => void;
  featuredFirst?: boolean;
}) {
  const filtered = useMemo(() => {
    if (topicFilter === "all") return paths;
    return paths.filter((p) => p.topic === topicFilter);
  }, [paths, topicFilter]);

  return (
    <section className="mt-10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-800">{title}</h2>
          <p className="mt-0.5 text-sm text-stone-500">
            Pre-tested combinations you can run in one click.
          </p>
        </div>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-medium uppercase tracking-wide text-stone-400">
            Topic
          </span>
          <select
            value={topicFilter}
            onChange={(e) => onTopicFilter(e.target.value)}
            className="rounded-lg border border-[#ddd0c0] bg-white px-3 py-2 text-sm text-stone-700 focus:border-pink-300 focus:outline-none focus:ring-2 focus:ring-pink-100"
          >
            <option value="all">All topics</option>
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      {filtered.length === 0 ? (
        <p className="mt-6 rounded-xl border border-[#e8ddd0] bg-white/60 px-4 py-8 text-center text-sm text-stone-500">
          No examples match this topic. Try another one.
        </p>
      ) : (
        <div className="mt-5 space-y-3">
          {filtered.map((path, i) => (
            <PathCard
              key={path.path_id}
              path={path}
              topics={topics}
              onUse={() => onUse(path)}
              featured={featuredFirst && i === 0}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ExploreContent() {
  const params = useSearchParams();
  const router = useRouter();
  const [question, setQuestion] = useState(() => params.get("q") ?? "");
  const [topics, setTopics] = useState<GuidedTopic[]>([]);
  const [browsePaths, setBrowsePaths] = useState<GuidedPathPair[]>([]);
  const [suggest, setSuggest] = useState<GuidedSuggestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topicFilter, setTopicFilter] = useState(() => params.get("topic") || "all");

  const hasSearch = Boolean(suggest && !loading);

  useEffect(() => {
    void getGuidedTopics().then(setTopics).catch(() => {});
    void getGuidedPaths().then(setBrowsePaths).catch(() => {});
  }, []);

  useEffect(() => {
    const q = params.get("q") ?? "";
    const topic = params.get("topic");
    if (topic) setTopicFilter(topic);
    if (q || topic) void runSuggest(q, topic ?? undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runSuggest(q: string, topic?: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await guidedSuggest(q, topic === "all" ? undefined : topic);
      setSuggest(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load suggestions.");
    } finally {
      setLoading(false);
    }
  }

  function syncUrl(q: string, topic: string) {
    const qs = new URLSearchParams();
    if (q.trim()) qs.set("q", q.trim());
    if (topic && topic !== "all") qs.set("topic", topic);
    router.replace(qs.toString() ? `/explore?${qs}` : "/explore", { scroll: false });
  }

  function goReview(path: GuidedPathPair) {
    const qs = new URLSearchParams({
      ids: path.resource_ids.join(","),
      pair: path.path_id,
    });
    if (path.user_intent) qs.set("intent", path.user_intent);
    router.push(`/review?${qs}`);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    syncUrl(question, topicFilter);
    void runSuggest(question.trim(), topicFilter === "all" ? undefined : topicFilter);
  }

  function onExample(ex: string) {
    setQuestion(ex);
    syncUrl(ex, topicFilter);
    void runSuggest(ex, topicFilter === "all" ? undefined : topicFilter);
  }

  function onTopicFilterChange(id: string) {
    setTopicFilter(id);
    if (hasSearch || question.trim()) {
      syncUrl(question, id);
      void runSuggest(question.trim(), id === "all" ? undefined : id);
    } else {
      syncUrl("", id);
    }
  }

  const displayPaths = hasSearch ? suggest!.recommended_pairs : browsePaths;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:max-w-3xl sm:py-12">
      <header className="text-center sm:text-left">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-800 sm:text-3xl">
          Explore by question
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-stone-600">
          Ask what you want to learn, or pick a tested example below.
        </p>
      </header>

      <form onSubmit={onSubmit} className="mt-8">
        <label className="sr-only" htmlFor="explore-question">
          Your question
        </label>
        <input
          id="explore-question"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Do richer countries have better health?"
          className="w-full rounded-2xl border border-[#ddd0c0] bg-white px-4 py-3.5 text-sm text-stone-800 shadow-sm placeholder:text-stone-400 focus:border-pink-300 focus:outline-none focus:ring-2 focus:ring-pink-100"
        />
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-stone-500">
            Try:{" "}
            {EXAMPLE_QUESTIONS.map((ex, i) => (
              <span key={ex}>
                {i > 0 && " · "}
                <button
                  type="button"
                  onClick={() => onExample(ex)}
                  className="font-medium text-pink-600 hover:text-pink-700"
                >
                  {ex}
                </button>
              </span>
            ))}
          </p>
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-pink-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-pink-700 disabled:opacity-50"
          >
            {loading ? "Searching…" : "Find matches"}
          </button>
        </div>
      </form>

      <p className="mt-6 text-center text-xs text-stone-400 sm:text-left">
        Prefer full control?{" "}
        <Link href="/search" className="font-medium text-stone-600 hover:text-pink-600">
          Browse the catalog
        </Link>
      </p>

      {error && (
        <p className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      {loading && (
        <div className="mt-10">
          <LoadingBlock message="Finding matches…" />
        </div>
      )}

      {!loading && hasSearch && suggest!.paraphrase && (
        <p className="mt-8 rounded-xl border border-[#e8ddd0] bg-white/70 px-4 py-3 text-sm text-stone-600">
          {suggest!.paraphrase}
        </p>
      )}

      {!loading && hasSearch && suggest!.fallback_message && (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {suggest!.fallback_message}
        </p>
      )}

      {!loading && displayPaths.length > 0 && (
        <PairingsSection
          title={hasSearch ? "Best matches" : "Example analyses"}
          paths={displayPaths}
          topics={topics}
          topicFilter={topicFilter}
          onTopicFilter={onTopicFilterChange}
          onUse={goReview}
          featuredFirst={hasSearch}
        />
      )}

      {!loading && hasSearch && suggest!.datasets.length > 0 && (
        <details className="group mt-10 rounded-2xl border border-[#e8ddd0] bg-white/50 open:bg-white">
          <summary className="cursor-pointer list-none px-4 py-4 text-sm font-medium text-stone-700 marker:content-none sm:px-5">
            <span className="flex items-center justify-between gap-2">
              Other individual datasets
              <span className="text-xs font-normal text-stone-400">
                {suggest!.datasets.length} match{suggest!.datasets.length === 1 ? "" : "es"}
              </span>
            </span>
          </summary>
          <ul className="space-y-2 border-t border-[#f0e8de] px-4 pb-4 pt-2 sm:px-5">
            {suggest!.datasets.slice(0, 8).map((d) => (
              <li
                key={d.id}
                className="flex flex-col gap-1 rounded-lg px-2 py-2 text-sm hover:bg-[#faf8f5] sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-stone-800">{d.title}</p>
                  {d.match_reason && (
                    <p className="truncate text-xs text-stone-500">{d.match_reason}</p>
                  )}
                </div>
                <Link
                  href={`/review?ids=${encodeURIComponent(d.id)}`}
                  className="shrink-0 text-xs font-semibold text-pink-600 hover:text-pink-700"
                >
                  Analyze →
                </Link>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

export default function ExplorePage() {
  return (
    <Suspense fallback={<LoadingBlock message="Loading explore…" minHeight="min-h-[40vh]" />}>
      <ExploreContent />
    </Suspense>
  );
}
