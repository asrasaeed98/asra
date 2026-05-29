import type { Metadata } from "next";
import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

export const metadata: Metadata = {
  title: `About · ${APP_NAME}`,
  description:
    "Why Findings exists: verifiable statistics on authoritative public data, explained in plain language.",
};

const AUDIENCE = [
  {
    title: "Analysts & researchers",
    description: "Defensible numbers fast, without building the data pipeline yourself.",
  },
  {
    title: "Journalists & policy",
    description: "Findings you can cite, each tied to a computed result and its source dataset.",
  },
  {
    title: "Everyone else",
    description:
      "PMs, comms, and domain experts get plain-language answers and a grounded chat, with no SQL required.",
  },
] as const;

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14 sm:py-16">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-600">About</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-800 sm:text-4xl">
        Statistics you can trust, from data you can cite
      </h1>
      <p className="mt-5 text-lg leading-relaxed text-stone-600">
        {APP_NAME} turns authoritative public data into real statistical findings, explained in
        plain language, with every number traceable back to a computed result. It exists for the
        moments when a plausible-sounding answer isn&apos;t good enough and you need one you can
        defend.
      </p>

      <section className="mt-12">
        <h2 className="text-xl font-semibold text-stone-800">What makes it different</h2>
        <p className="mt-3 leading-relaxed text-stone-600">
          The hard, risky part of data analysis isn&apos;t writing prose; it&apos;s getting
          trustworthy data, computing rigorous statistics, and being able to show your work.{" "}
          {APP_NAME} is built for exactly that. Every finding is a real test (a correlation, a group
          comparison, a trend, a chi-square, or an ML pattern), reported with its sample size,
          p-value, effect size, and the exact query that produced it. The AI summarizes and answers
          questions about those results, but it is blocked from inventing numbers.
        </p>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-semibold text-stone-800">Built to be read by anyone</h2>
        <p className="mt-3 leading-relaxed text-stone-600">
          Results lead with a plain-language summary and the key patterns, then let you ask follow-up
          questions in a grounded chat. The full methodology (fields analyzed, data dictionary, and
          test details) is always one click away, so technical and non-technical readers get what
          they each need from the same report.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {AUDIENCE.map(({ title, description }) => (
            <div key={title} className="rounded-2xl border border-[#e8ddd0] bg-white/80 p-5 shadow-sm">
              <h3 className="text-base font-semibold text-stone-800">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-stone-600">{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-semibold text-stone-800">Where the data comes from</h2>
        <p className="mt-3 leading-relaxed text-stone-600">
          {APP_NAME} connects to authoritative public sources: the U.S. open-data catalog
          (data.gov), the Federal Reserve&apos;s economic data (FRED), and the World Bank. Each
          dataset carries its license and attribution, and only ingestible, well-formed files are
          offered for analysis.
        </p>
      </section>

      <section className="mt-12 rounded-2xl border border-[#e8ddd0] bg-[#faf8f5] p-6 text-center">
        <h2 className="text-lg font-semibold text-stone-800">Try it on a question you care about</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
          Pick a public dataset or two and get ranked, verifiable findings in a couple of minutes.
        </p>
        <div className="mt-5">
          <Link
            href="/search"
            className="inline-block rounded-xl bg-pink-600 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-pink-200/50 transition hover:bg-pink-700"
          >
            Search datasets
          </Link>
        </div>
      </section>
    </div>
  );
}
