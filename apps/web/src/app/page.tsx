import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <p className="text-sm font-medium text-emerald-700">Phase 1 prototype</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight">
        From open data to trusted findings
      </h1>
      <p className="mt-4 text-lg text-zinc-600">
        Search curated public datasets, run automated analysis with clear statistics
        and clustering, and explore results with visuals, an AI summary, and
        grounded chat.
      </p>
      <ul className="mt-8 space-y-2 text-zinc-700">
        <li>Strict license-safe catalog (CC0 / public domain)</li>
        <li>Computed metrics you can verify — AI explains, never invents numbers</li>
        <li>1–2 datasets per analysis session</li>
      </ul>
      <div className="mt-10 flex flex-wrap gap-4">
        <Link
          href="/search"
          className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-800"
        >
          Search datasets
        </Link>
        <a
          href="/docs/findings-ai"
          className="rounded-lg border border-zinc-300 px-5 py-2.5 text-sm font-medium hover:bg-white"
        >
          Product docs (repo)
        </a>
      </div>
      <p className="mt-12 text-sm text-zinc-500">
        API health:{" "}
        <code className="rounded bg-zinc-100 px-1">
          {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health
        </code>
      </p>
    </div>
  );
}
