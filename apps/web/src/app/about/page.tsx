import type { Metadata } from "next";
import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

export const metadata: Metadata = {
  title: `About · ${APP_NAME}`,
  description:
    "Findings makes public data easier to understand: trusted open datasets, statistical analysis, and plain-language explanations.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14 sm:py-16">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-600">About</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-800 sm:text-4xl">
        Making public data easier to understand
      </h1>
      <p className="mt-5 text-lg leading-relaxed text-stone-600">
        {APP_NAME} exists because public data should be useful to everyone, not just data
        specialists. It connects to trusted open datasets, runs statistical analysis, and explains
        the results in plain language so you can answer questions with evidence.
      </p>

      <section className="mt-10 space-y-8">
        <div>
          <h2 className="text-lg font-semibold text-stone-800">What you get</h2>
          <p className="mt-2 leading-relaxed text-stone-600">
            Choose one or two datasets and ask a question. {APP_NAME} returns ranked findings,
            visualizations, and clear explanations you can understand without a statistics
            background. Every finding is backed by a computed result and linked to its underlying
            data.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-stone-800">Where the data comes from</h2>
          <p className="mt-2 leading-relaxed text-stone-600">
            {APP_NAME} uses authoritative public datasets, including{" "}
            <a
              href="https://catalog.data.gov"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-pink-600 hover:text-pink-700"
            >
              data.gov
            </a>
            , the{" "}
            <a
              href="https://fred.stlouisfed.org"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-pink-600 hover:text-pink-700"
            >
              Federal Reserve (FRED)
            </a>
            , the{" "}
            <a
              href="https://data.worldbank.org"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-pink-600 hover:text-pink-700"
            >
              World Bank
            </a>
            , and{" "}
            <a
              href="https://opendata.cityofnewyork.us/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-pink-600 hover:text-pink-700"
            >
              NYC Open Data
            </a>
            . Each dataset includes its source and licensing information. {APP_NAME} is an
            independent project and is not affiliated with, endorsed by, or sponsored by these
            providers.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-stone-800">Built by</h2>
          <p className="mt-2 leading-relaxed text-stone-600">
            {APP_NAME} is built by{" "}
            <a
              href="https://www.linkedin.com/in/asrasaeed/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-pink-600 hover:text-pink-700"
            >
              Asra Saeed
            </a>
            . I started it because I love using data to answer questions, and I believe more people
            should be able to explore public data and uncover meaningful insights without needing to
            be a statistician. {APP_NAME} is my attempt to make rigorous analysis more accessible,
            transparent, and easy to understand.
          </p>
          <p className="mt-3 leading-relaxed text-stone-600">
            If you have feedback, questions, or ideas, I&apos;d love to hear from you!
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-stone-800">Who it&apos;s for</h2>
          <p className="mt-2 leading-relaxed text-stone-600">
            Anyone curious about what public data can tell us, from journalists and students to
            policy staff, researchers, community organizers, and everyday users. If the data is
            open, you shouldn&apos;t need a data team to learn from it.
          </p>
        </div>
      </section>

      <section className="mt-12 rounded-2xl border border-[#e8ddd0] bg-[#faf8f5] p-6 text-center">
        <h2 className="text-lg font-semibold text-stone-800">Try it</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
          Browse open datasets or start with a question you care about.
        </p>
        <div className="mt-5 flex flex-col items-center gap-2.5 sm:flex-row sm:justify-center sm:gap-3">
          <Link
            href="/search"
            className="inline-block rounded-xl bg-pink-600 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-pink-200/50 transition hover:bg-pink-700"
          >
            Browse datasets
          </Link>
          <Link
            href="/explore"
            className="inline-block rounded-xl border border-[#ddd0c0] bg-white px-6 py-3 text-sm font-semibold text-stone-700 transition hover:border-pink-200 hover:text-pink-700"
          >
            Ask a question
          </Link>
        </div>
      </section>
    </div>
  );
}
