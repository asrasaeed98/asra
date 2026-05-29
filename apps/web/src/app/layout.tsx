import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import { APP_NAME } from "@/lib/app-name";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: APP_NAME,
  description:
    "Search open datasets, run trustworthy analysis, and explore insights with visuals and grounded chat.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} flex min-h-screen flex-col antialiased text-stone-700`}
      >
        <header className="border-b border-[#e8ddd0] bg-[#fffcf8]/95 backdrop-blur-md">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight text-stone-800">
              {APP_NAME}
              <span className="text-pink-500">.</span>
            </Link>
            <nav className="flex items-center gap-5">
              <Link
                href="/"
                className="text-sm font-medium text-stone-600 transition-colors hover:text-pink-600"
              >
                Home
              </Link>
              <Link
                href="/about"
                className="text-sm font-medium text-stone-600 transition-colors hover:text-pink-600"
              >
                About
              </Link>
              <Link
                href="/search"
                className="rounded-lg bg-pink-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-pink-700"
              >
                Search datasets
              </Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-[#e8ddd0] bg-[#fffcf8]/80">
          <div className="mx-auto max-w-5xl px-4 py-4 text-center text-xs text-stone-400">
            Phase 1 prototype
          </div>
        </footer>
      </body>
    </html>
  );
}
