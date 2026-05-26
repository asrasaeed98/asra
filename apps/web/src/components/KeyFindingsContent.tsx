"use client";

import type { SummaryBlock } from "@/lib/summary-format";

export function KeyFindingsContent({ blocks }: { blocks: SummaryBlock[] }) {
  if (blocks.length === 0) {
    return <p className="mt-2 text-sm text-stone-600">Summary will appear when analysis completes.</p>;
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
