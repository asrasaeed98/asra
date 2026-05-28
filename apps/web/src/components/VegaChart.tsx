"use client";

import { useEffect, useRef } from "react";

type VegaChartProps = {
  spec: Record<string, unknown>;
  title: string;
};

function hasChartValues(spec: Record<string, unknown>): boolean {
  const data = spec.data;
  if (!data || typeof data !== "object") return false;
  const values = (data as { values?: unknown[] }).values;
  return Array.isArray(values) && values.length > 0;
}

export function VegaChart({ spec, title }: VegaChartProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !hasChartValues(spec)) return;

    let view: { finalize: () => void } | undefined;

    void import("vega-embed").then(({ default: embed }) =>
      embed(el, spec, {
        actions: { export: true, source: false, compiled: false, editor: false },
        renderer: "svg",
      }).then((result) => {
        view = result.view;
      }),
    );

    return () => {
      view?.finalize();
    };
  }, [spec]);

  if (!hasChartValues(spec)) {
    return <p className="text-xs text-stone-500">No chart data available.</p>;
  }

  return (
    <div
      ref={ref}
      className="w-full overflow-x-auto [&_svg]:mx-auto"
      role="img"
      aria-label={title}
    />
  );
}
