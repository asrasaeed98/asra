import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

export function SiteFooter() {
  return (
    <footer className="border-t border-[#e8ddd0] bg-[#fffcf8]/80">
      <div className="mx-auto max-w-5xl px-4 py-5 text-center text-xs text-stone-400">
        <p>Phase 1 prototype</p>
        <nav className="mt-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
          <Link href="/about" className="text-stone-500 transition hover:text-pink-600">
            About
          </Link>
          <span aria-hidden="true">·</span>
          <Link href="/terms" className="text-stone-500 transition hover:text-pink-600">
            Terms
          </Link>
          <span aria-hidden="true">·</span>
          <Link href="/privacy" className="text-stone-500 transition hover:text-pink-600">
            Privacy
          </Link>
        </nav>
        <p className="mx-auto mt-3 max-w-2xl leading-relaxed text-stone-400">
          {APP_NAME} is an independent project and is not affiliated with, endorsed by, or
          sponsored by data.gov, the Federal Reserve, the World Bank, NYC Open Data, or other
          listed data providers.
        </p>
      </div>
    </footer>
  );
}
