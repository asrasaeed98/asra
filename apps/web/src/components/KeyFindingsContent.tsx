"use client";

import type { SummaryBlock } from "@/lib/summary-format";

function SummarySkeleton() {
  return (
    <div className="mt-3 space-y-3 animate-pulse" aria-hidden="true">
      <div className="h-3 w-full rounded bg-[#e8ddd0]" />
      <div className="h-3 w-11/12 rounded bg-[#e8ddd0]" />
      <div className="h-3 w-4/5 rounded bg-[#e8ddd0]" />
      <div className="mt-4 h-3 w-full rounded bg-[#e8ddd0]" />
      <div className="h-3 w-10/12 rounded bg-[#e8ddd0]" />
    </div>
  );
}

export function KeyFindingsContent({
  blocks,
  loading = false,
}: {
  blocks: SummaryBlock[];
  loading?: boolean;
}) {
  if (loading) {
    return <SummarySkeleton />;
  }

  if (blocks.length === 0) {
    return (
      <p className="mt-2 text-sm text-stone-600">
        No summary was generated for this session.
      </p>
    );
  }

  return (
    <div className="mt-3 space-y-4 text-sm leading-relaxed text-stone-700">
      {blocks.map((block, i) => {
        if (block.type === "paragraph") {
          return (
            <p key={`p-${i}-${block.text.slice(0, 24)}`} className="leading-relaxed">
              {block.text}
            </p>
          );
        }
        return (
          <ul key={`ul-${i}`} className="list-disc space-y-2 pl-5 marker:text-pink-400">
            {block.items.map((item) => (
              <li key={item.slice(0, 48)} className="pl-0.5">
                {item}
              </li>
            ))}
          </ul>
        );
      })}
    </div>
  );
}
