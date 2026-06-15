"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

type FindingsLoaderProps = {
  message?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizes = { sm: 48, md: 80, lg: 120 };

export function FindingsLoader({
  message = "Working on it…",
  size = "md",
  className = "",
}: FindingsLoaderProps) {
  const [useGif, setUseGif] = useState(false);
  const px = sizes[size];

  useEffect(() => {
    fetch("/findings-loader.gif", { method: "HEAD" })
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
          src="/findings-loader.gif"
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
          <ellipse cx="60" cy="68" rx="42" ry="38" fill="#f5efe6" />
          <ellipse cx="60" cy="70" rx="36" ry="32" fill="#e8ddd0" />
          <circle cx="45" cy="58" r="5" fill="#57534e" />
          <circle cx="75" cy="58" r="5" fill="#57534e" />
          <path
            d="M 48 72 Q 60 82 72 72"
            fill="none"
            stroke="#e879a9"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle className="ff-animate-sparkle" cx="28" cy="32" r="6" fill="#f472b6" />
          <circle className="ff-animate-sparkle" cx="92" cy="28" r="5" fill="#ec4899" />
          <circle className="ff-animate-sparkle" cx="60" cy="18" r="4" fill="#e879a9" />
        </svg>
      )}
      <p className="text-center text-sm font-medium text-stone-600">{message}</p>
      <span className="sr-only">Loading</span>
    </div>
  );
}
