import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <p className="text-sm font-medium text-pink-500">Phase 1 prototype</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-800">
        Find insights in <span className="text-pink-600">open data</span>
      </h1>
      <p className="mt-4 text-lg text-slate-600">
        {APP_NAME} helps you search public datasets, run automatic analysis you can
        trust, and explore results with clear charts and grounded chat.
      </p>
      <ul className="mt-8 space-y-2 text-slate-600">
        <li className="flex gap-2">
          <span className="text-pink-400">✦</span> License-safe catalog
        </li>
        <li className="flex gap-2">
          <span className="text-pink-400">✦</span> Computed numbers — AI explains, never invents stats
        </li>
        <li className="flex gap-2">
          <span className="text-pink-400">✦</span> Up to 2 datasets per analysis
        </li>
      </ul>
      <div className="mt-10">
        <Link
          href="/search"
          className="inline-block rounded-xl bg-pink-600 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-pink-200 transition hover:bg-pink-700"
        >
          Search datasets
        </Link>
      </div>
    </div>
  );
}
