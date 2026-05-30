import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import { APP_NAME } from "@/lib/app-name";
import "./globals.css";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

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
        className={`${geistSans.variable} ${geistMono.variable} flex min-h-screen flex-col overflow-x-hidden antialiased text-stone-700`}
      >
        <header className="border-b border-[#e8ddd0] bg-[#fffcf8]/95 backdrop-blur-md">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:py-4">
            <Link href="/" className="text-base font-semibold tracking-tight text-stone-800 sm:text-lg">
              {APP_NAME}
              <span className="text-pink-500">.</span>
            </Link>
            <nav className="flex items-center gap-4 sm:gap-5">
              <Link
                href="/"
                className="text-sm font-medium text-stone-600 transition-colors hover:text-pink-600"
              >
                Home
              </Link>
              <Link
                href="/explore"
                className="text-sm font-medium text-stone-600 transition-colors hover:text-pink-600"
              >
                Explore
              </Link>
              <Link
                href="/search"
                className="text-sm font-medium text-stone-600 transition-colors hover:text-pink-600"
              >
                Search
              </Link>
              <Link
                href="/about"
                className="text-sm font-medium text-stone-600 transition-colors hover:text-pink-600"
              >
                About
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
