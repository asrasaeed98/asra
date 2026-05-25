"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

type FunFindsLoaderProps = {
  message?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizes = { sm: 48, md: 80, lg: 120 };

/** Cute loader: uses /funfinds-loader.gif if present, else animated SVG mascot. */
export function FunFindsLoader({
  message = "Working on it…",
  size = "md",
  className = "",
}: FunFindsLoaderProps) {
  const [useGif, setUseGif] = useState(false);
  const px = sizes[size];

  useEffect(() => {
    fetch("/funfinds-loader.gif", { method: "HEAD" })
      .then((r) => setUseGif(r.ok))
      .catch(() => setUseGif(false));
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center gap-3 ${className}`}
    >
      {useGif ? (
        <Image
          src="/funfinds-loader.gif"
          alt=""
          width={px}
          height={px}
          unoptimized
          className="ff-animate-bounce rounded-2xl"
        />
      ) : (
        <svg
          width={px}
          height={px}
          viewBox="0 0 120 120"
          aria-hidden
          className="ff-animate-bounce"
        >
          <ellipse cx="60" cy="68" rx="42" ry="38" fill="#fbcfe8" />
          <ellipse cx="60" cy="70" rx="36" ry="32" fill="#f9a8d4" />
          <circle cx="45" cy="58" r="5" fill="#831843" />
          <circle cx="75" cy="58" r="5" fill="#831843" />
          <path
            d="M 48 72 Q 60 82 72 72"
            fill="none"
            stroke="#be185d"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle
            className="ff-animate-sparkle"
            cx="28"
            cy="32"
            r="6"
            fill="#ec4899"
            style={{ animationDelay: "0s" }}
          />
          <circle
            className="ff-animate-sparkle"
            cx="92"
            cy="28"
            r="5"
            fill="#f472b6"
            style={{ animationDelay: "0.3s" }}
          />
          <circle
            className="ff-animate-sparkle"
            cx="60"
            cy="18"
            r="4"
            fill="#db2777"
            style={{ animationDelay: "0.6s" }}
          />
        </svg>
      )}
      <p className="text-center text-sm font-medium text-pink-700">{message}</p>
      <span className="sr-only">Loading</span>
    </div>
  );
}
