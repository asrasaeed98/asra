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
  "Plain-language summary of the strongest patterns",
  "Charts linked to each finding",
  "Chat to ask follow-up questions about your results",
  "Full report with tests, p-values, and data sources",
] as const;

const STEPS = [
  {
    step: 1,
    title: "Pick public datasets",
    description:
      "Browse open catalogs like data.gov, FRED, World Bank, and NYC Open Data, with license checks built in. We pull the data and handle cleaning and joins.",
    descriptionShort:
      "Browse data.gov, FRED, World Bank, and NYC Open Data. We handle cleaning and joins.",
  },
  {
    step: 2,
    title: "We run the analysis",
    description:
      "Real statistical tests (correlations, group differences, trends, and more) plus machine-learning patterns. Every result includes its p-value, sample size, and the query behind it.",
    descriptionShort:
      "Correlations, trends, group tests, and ML patterns, each with p-values and sample sizes.",
  },
  {
    step: 3,
    title: "Get evidence-backed findings",
    description:
      "The strongest patterns first, explained in plain language, with every number traceable to a result. Ask follow-up questions in a grounded chat.",
    descriptionShort:
      "Ranked findings in plain language, plus grounded chat for follow-ups.",
  },
] as const;

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:py-16">
      <section className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-800 sm:text-5xl">
          Turn public datasets into{" "}
          <span className="bg-gradient-to-r from-pink-600 to-pink-400 bg-clip-text text-transparent">
            findings you can trust
          </span>
          .
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-stone-600 sm:mt-5 sm:text-lg">
          Ask a question, analyze trusted public datasets, and uncover statistically-backed findings
          with charts, explanations, and a complete analysis report.
        </p>
        <div className="mt-6 flex flex-col items-center gap-2.5 sm:mt-8 sm:flex-row sm:justify-center sm:gap-3">
          <Link
            href="/search"
            className="inline-flex w-44 items-center justify-center rounded-lg bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-pink-200/50 transition hover:bg-pink-700 sm:w-auto sm:rounded-xl sm:px-7 sm:py-3"
          >
            Browse datasets
          </Link>
          <Link
            href="/explore"
            className="inline-flex w-44 items-center justify-center rounded-lg border border-[#ddd0c0] bg-white px-4 py-2.5 text-sm font-semibold text-stone-700 transition hover:border-pink-200 hover:text-pink-700 sm:w-auto sm:rounded-xl sm:px-7 sm:py-3"
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
              Every analysis includes
            </p>
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
          Open data should be useful to more than data scientists
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
          Governments and institutions publish vast amounts of public data, but most people never
          get to use it. {APP_NAME} lowers the barrier with real statistics, licensed sources, and
          answers you can read and share.
        </p>
      </section>
    </div>
  );
}
