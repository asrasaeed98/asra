import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

const VALUE_PROPS = [
  {
    step: 1,
    title: "Select up to 2 datasets",
    description: "Choose one or two public tables for each analysis.",
  },
  {
    step: 2,
    title: "Run analysis, get ranked results",
    description:
      "We compute the statistics first, then rank the strongest patterns. AI summaries explain what the numbers mean, grounded in your results and never inventing figures.",
  },
  {
    step: 3,
    title: "Search real licensed datasets",
    description:
      "Browse vetted public catalogs with license labels and ingestible file checks.",
  },
] as const;

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14 sm:py-20">
      <section className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-600">
          Open data → insights
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-stone-800 sm:text-5xl">
          Find insights in{" "}
          <span className="bg-gradient-to-r from-pink-600 to-pink-400 bg-clip-text text-transparent">
            open data
          </span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-lg leading-relaxed text-stone-600">
          {APP_NAME} helps researchers, journalists, and curious analysts turn public datasets
          into ranked findings you can trust, with plain-language summaries tied to real numbers.
        </p>
        <div className="mt-8">
          <Link
            href="/search"
            className="inline-block rounded-xl bg-pink-600 px-7 py-3.5 text-sm font-semibold text-white shadow-md shadow-pink-200/50 transition hover:bg-pink-700"
          >
            Search datasets
          </Link>
        </div>
      </section>

      <section className="mt-14 sm:mt-16">
        <h2 className="text-center text-sm font-semibold uppercase tracking-wide text-stone-500">
          How it works
        </h2>
        <ol className="mt-6 space-y-4">
          {VALUE_PROPS.map(({ step, title, description }) => (
            <li
              key={step}
              className="flex gap-4 rounded-2xl border border-[#e8ddd0] bg-white/80 p-5 shadow-sm backdrop-blur-sm sm:gap-5 sm:p-6"
            >
              <span
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-pink-100 text-sm font-bold text-pink-700"
                aria-hidden="true"
              >
                {step}
              </span>
              <div className="min-w-0 text-left">
                <h3 className="text-base font-semibold text-stone-800">{title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-stone-600">{description}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
