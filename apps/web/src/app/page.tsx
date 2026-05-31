import Image from "next/image";
import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

const EXAMPLE_QUESTIONS = [
  {
    label: "What factors are associated with life expectancy?",
    href: "/explore?q=What+factors+are+associated+with+life+expectancy%3F",
  },
  {
    label: "Does education correlate with income?",
    href: "/explore?q=Does+education+correlate+with+income%3F",
  },
  {
    label: "How does literacy relate to internet access?",
    href: "/explore?q=How+does+literacy+relate+to+internet+access%3F",
  },
  {
    label: "How have housing costs changed over time?",
    href: "/explore?q=How+have+housing+costs+changed+over+time%3F",
  },
] as const;

const OUTPUTS = [
  "AI Summary of ranked key findings",
  "Auto-generated charts linked to each finding",
  "LLM-powered chat grounded in your results",
  "Full analysis report with tests, p-values, and sources",
] as const;

const STEPS = [
  {
    step: 1,
    title: "Search real, licensed datasets",
    description:
      "Browse vetted public catalogs (data.gov, FRED, World Bank) with license checks. We pull the data in and handle cleaning and joins for you.",
    descriptionShort:
      "Browse data.gov, FRED, and World Bank. We handle cleaning and joins.",
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
    descriptionShort:
      "Ranked findings in plain language, plus grounded chat for follow-ups.",
  },
] as const;

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:py-16">
      <section className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-pink-600 sm:tracking-[0.2em]">
          Insights from open data
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-800 sm:mt-4 sm:text-5xl">
          Ask a question.{" "}
          <span className="bg-gradient-to-r from-pink-600 to-pink-400 bg-clip-text text-transparent">
            Get findings you can trust
          </span>
          .
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-stone-600 sm:mt-5 sm:text-lg">
          {APP_NAME} joins public datasets, runs real statistical tests, and returns ranked,
          plain-language answers with charts and a full analysis report.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:mt-8 sm:flex-row sm:justify-center">
          <Link
            href="/search"
            className="inline-block w-full max-w-xs rounded-xl bg-pink-600 px-7 py-3.5 text-center text-sm font-semibold text-white shadow-md shadow-pink-200/50 transition hover:bg-pink-700 sm:w-auto"
          >
            Browse datasets
          </Link>
          <Link
            href="/explore"
            className="inline-block w-full max-w-xs rounded-xl border border-[#ddd0c0] bg-white px-7 py-3.5 text-center text-sm font-semibold text-stone-700 transition hover:border-pink-200 hover:text-pink-700 sm:w-auto"
          >
            Ask a question
          </Link>
        </div>
      </section>

      <section className="mt-12 sm:mt-16">
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

      <section className="mt-12 rounded-3xl border border-pink-100 bg-gradient-to-b from-pink-50 to-pink-50/40 p-6 shadow-xl shadow-pink-200/50 sm:mt-16 sm:p-8">
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-[#e8ddd0] bg-white px-5 py-5 text-left shadow-sm sm:px-6 sm:py-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-pink-700">
              Example finding
            </p>
            <p className="mt-2 text-sm leading-relaxed text-stone-800 sm:text-base">
              <span className="font-semibold">Moderate positive association</span> between adult
              literacy and internet usage (Spearman{" "}
              <span className="font-mono text-sm">r = 0.63</span>,{" "}
              <span className="font-mono text-sm">n = 1,538</span>). Countries with higher literacy
              tend to have higher internet adoption.
            </p>
            <p className="mt-4 text-sm font-medium text-stone-700">Every analysis includes:</p>
            <ul className="mt-2 flex flex-col gap-1.5 text-sm text-stone-600">
              {OUTPUTS.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-pink-500" aria-hidden="true">
                    ✓
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="hidden overflow-hidden rounded-2xl border border-[#e8ddd0] bg-white shadow-sm md:block">
            <Image
              src="/home/key-findings-literacy-internet.png"
              alt="Results page showing key findings, grounded chat, and analysis report from a literacy and internet usage analysis"
              width={1548}
              height={1744}
              className="h-auto w-full"
              priority
            />
          </div>

          <div className="overflow-hidden rounded-2xl border border-[#e8ddd0] bg-white shadow-sm">
            <Image
              src="/home/chart-literacy-internet.png"
              alt="Scatter chart showing moderate positive association between adult literacy rate and internet usage, Spearman r = 0.63"
              width={2400}
              height={900}
              className="h-auto w-full"
            />
          </div>
        </div>
      </section>

      <section className="mt-12 sm:mt-16">
        <h2 className="text-center text-sm font-semibold uppercase tracking-wide text-stone-500">
          Questions you can ask
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-sm text-stone-600">
          Start with a question. {APP_NAME} suggests datasets and runs the analysis.
        </p>
        <ul className="mt-5 flex flex-wrap justify-center gap-2.5">
          {EXAMPLE_QUESTIONS.map(({ label, href }) => (
            <li key={href}>
              <Link
                href={href}
                className="inline-block rounded-full border border-[#e8ddd0] bg-white px-4 py-2 text-sm text-stone-700 transition hover:border-pink-200 hover:bg-pink-50 hover:text-pink-800"
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12 rounded-2xl border border-[#e8ddd0] bg-[#faf8f5] p-6 text-center sm:mt-16">
        <h2 className="text-lg font-semibold text-stone-800">
          Built for people who need answers from public data
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
          Policy analysts, researchers, and journalists use {APP_NAME} when they need defensible
          insights, not black-box summaries. Computed statistics, licensed sources, full traceability.
        </p>
      </section>
    </div>
  );
}
