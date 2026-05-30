import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

const STEPS = [
  {
    step: 1,
    title: "Search real, licensed datasets",
    description:
      "Browse vetted public catalogs (data.gov, FRED, World Bank) with license checks. We pull the data in and handle cleaning and joins for you.",
    descriptionShort: "Browse data.gov, FRED, and World Bank. We handle cleaning and joins.",
  },
  {
    step: 2,
    title: "We compute the statistics",
    description:
      "Real statistical tests, including correlations, group differences, time trends, and category associations, plus machine-learning models that surface clusters and hidden patterns. Each result carries its p-value, sample size, and the query behind it, so the numbers are computed, not guessed.",
    descriptionShort:
      "Correlations, trends, group tests, and ML patterns, each with p-values and sample sizes.",
  },
  {
    step: 3,
    title: "Get ranked, plain-language findings",
    description:
      "The strongest patterns first, explained simply, with every number traceable to a result, plus a grounded chat for follow-up questions.",
    descriptionShort: "Ranked findings in plain language, plus grounded chat for follow-ups.",
  },
] as const;

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:py-20">
      <section className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-pink-600 sm:tracking-[0.2em]">
          Insights from open data
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-800 sm:mt-4 sm:text-5xl">
          Turn public data into{" "}
          <span className="bg-gradient-to-r from-pink-600 to-pink-400 bg-clip-text text-transparent">
            findings you can trust
          </span>
          .
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-stone-600 sm:hidden">
          Search public data, run real statistics, get plain-language answers you can verify.
        </p>
        <p className="mx-auto mt-5 hidden max-w-xl text-lg leading-relaxed text-stone-600 sm:block">
          {APP_NAME} searches authoritative public datasets, runs real statistical tests, and
          explains the results in plain language, with every number traceable to a computed result.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:mt-8 sm:flex-row sm:justify-center">
          <Link
            href="/explore"
            className="inline-block w-full max-w-xs rounded-xl bg-pink-600 px-7 py-3.5 text-center text-sm font-semibold text-white shadow-md shadow-pink-200/50 transition hover:bg-pink-700 sm:w-auto"
          >
            Ask a question
          </Link>
          <Link
            href="/search"
            className="inline-block w-full max-w-xs rounded-xl border border-[#ddd0c0] bg-white px-7 py-3.5 text-center text-sm font-semibold text-stone-700 transition hover:border-pink-200 hover:text-pink-700 sm:w-auto"
          >
            Browse datasets
          </Link>
        </div>
        <p className="mt-3 text-center text-xs text-stone-500">
          Guided explore for questions · Search for technical browsing
        </p>
      </section>

      <section className="mt-10 sm:mt-16">
        <h2 className="text-center text-sm font-semibold uppercase tracking-wide text-stone-500">
          How it works
        </h2>
        <ol className="mt-5 space-y-3 sm:mt-6 sm:space-y-4">
          {STEPS.map(({ step, title, description, descriptionShort }) => (
            <li
              key={step}
              className="flex gap-3 rounded-2xl border border-[#e8ddd0] bg-white/80 p-4 shadow-sm backdrop-blur-sm sm:gap-5 sm:p-6"
            >
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-pink-100 text-sm font-bold text-pink-700 sm:h-10 sm:w-10"
                aria-hidden="true"
              >
                {step}
              </span>
              <div className="min-w-0 text-left">
                <h3 className="text-sm font-semibold text-stone-800 sm:text-base">{title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-stone-600 sm:hidden">
                  {descriptionShort}
                </p>
                <p className="mt-1.5 hidden text-sm leading-relaxed text-stone-600 sm:block">
                  {description}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-10 hidden rounded-2xl border border-[#e8ddd0] bg-[#faf8f5] p-6 text-center sm:mt-16 sm:block">
        <h2 className="text-lg font-semibold text-stone-800">Built for analysts and the rest of the team</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
          Rigorous enough for researchers, journalists, and policy work, yet readable enough for
          anyone who just needs the answer. Plain-language summaries up top, the methodology a click
          away.
        </p>
      </section>
    </div>
  );
}
