import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "TokenTrim",
  description:
    "Leaner prompts, lower token cost. Three rewrites that cut tokens without losing meaning.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen antialiased text-stone-700`}
      >
        <header className="border-b border-[#e8ddd0] bg-[#fffcf8]/90 backdrop-blur-md">
          <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
            <div>
              <p className="text-lg font-semibold tracking-tight text-stone-800">
                TokenTrim<span className="text-violet-600">.</span>
              </p>
              <p className="text-xs text-stone-500">Leaner prompts, lower token cost</p>
            </div>
            <a
              href="https://github.com/asrasaeed98/asra"
              className="text-sm font-medium text-stone-500 transition-colors hover:text-violet-600"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </a>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
