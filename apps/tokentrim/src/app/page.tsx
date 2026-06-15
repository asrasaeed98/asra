"use client";

import { useState } from "react";
import type { PromptVariant, RefineResponse } from "@/lib/types";
import { VARIANT_LABELS } from "@/lib/types";

const inputClass =
  "w-full rounded-xl border border-[#e8ddd0] bg-white/80 px-3 py-2.5 text-sm text-stone-800 shadow-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-100";

const labelClass = "mb-1.5 block text-xs font-semibold uppercase tracking-wide text-stone-500";

function VariantCard({ variant, index }: { variant: PromptVariant; index: number }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(variant.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <article
      className="animate-fade-up rounded-2xl border border-[#e8ddd0] bg-white/90 p-5 shadow-sm"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600">
            {VARIANT_LABELS[variant.id] ?? variant.title}
          </p>
          <p className="mt-1 text-sm text-stone-500">{variant.rationale}</p>
        </div>
        <button
          type="button"
          onClick={copy}
          className="shrink-0 rounded-lg border border-[#e8ddd0] bg-[#faf8f5] px-3 py-1.5 text-xs font-medium text-stone-600 transition hover:border-violet-300 hover:text-violet-700"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      <pre className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap rounded-xl bg-stone-50 p-4 font-mono text-sm leading-relaxed text-stone-800">
        {variant.prompt}
      </pre>

      {variant.practices.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-stone-500">
          {variant.practices.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="text-violet-400">·</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

export default function HomePage() {
  const [prompt, setPrompt] = useState("");
  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [outputFormat, setOutputFormat] = useState("");
  const [constraints, setConstraints] = useState("");
  const [extraContext, setExtraContext] = useState("");
  const [showContext, setShowContext] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RefineResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/refine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          goal: goal || undefined,
          audience: audience || undefined,
          outputFormat: outputFormat || undefined,
          constraints: constraints || undefined,
          extraContext: extraContext || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Request failed");
      }
      setResult(data as RefineResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-800 sm:text-3xl">
          Same intent. Fewer tokens.
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
          Paste a bloated prompt. Get three lean rewrites — each optimized to cut tokens while
          keeping your meaning. Built for people who pay per API call.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="prompt" className={labelClass}>
            Your prompt <span className="text-violet-600">*</span>
          </label>
          <textarea
            id="prompt"
            required
            rows={6}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. I need help writing a product email that sounds friendly but professional..."
            className={`${inputClass} resize-y`}
          />
        </div>

        <button
          type="button"
          onClick={() => setShowContext((v) => !v)}
          className="text-sm font-medium text-violet-600 transition hover:text-violet-800"
        >
          {showContext ? "Hide optional context" : "+ Add optional context"}
        </button>

        {showContext && (
          <div className="grid gap-4 rounded-2xl border border-dashed border-[#e8ddd0] bg-white/50 p-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="goal" className={labelClass}>
                Goal
              </label>
              <input
                id="goal"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="What should the output accomplish?"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="audience" className={labelClass}>
                Audience
              </label>
              <input
                id="audience"
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                placeholder="Who is this for?"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="outputFormat" className={labelClass}>
                Output format
              </label>
              <input
                id="outputFormat"
                value={outputFormat}
                onChange={(e) => setOutputFormat(e.target.value)}
                placeholder="e.g. bullet list, JSON, 3 paragraphs"
                className={inputClass}
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="constraints" className={labelClass}>
                Constraints
              </label>
              <input
                id="constraints"
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
                placeholder="Length, tone, things to avoid..."
                className={inputClass}
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="extraContext" className={labelClass}>
                Extra context
              </label>
              <textarea
                id="extraContext"
                rows={3}
                value={extraContext}
                onChange={(e) => setExtraContext(e.target.value)}
                placeholder="Background facts, examples, domain details..."
                className={`${inputClass} resize-y`}
              />
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="w-full rounded-xl bg-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:px-8"
        >
          {loading ? "Trimming…" : "Get 3 lean prompts"}
        </button>
      </form>

      {error && (
        <p className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {result && (
        <section className="mt-10 space-y-6">
          <p className="text-sm text-stone-600">{result.summary}</p>
          <div className="space-y-5">
            {result.variants.map((variant, i) => (
              <VariantCard key={variant.id} variant={variant} index={i} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
