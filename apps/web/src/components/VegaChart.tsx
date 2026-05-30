"use client";

import { useEffect, useRef } from "react";

type VegaChartProps = {
  spec: Record<string, unknown>;
  title: string;
};

type VegaView = {
  resize: () => VegaView;
  run: () => void;
  finalize: () => void;
};

function hasChartValues(spec: Record<string, unknown>): boolean {
  const data = spec.data;
  if (!data || typeof data !== "object") return false;
  const values = (data as { values?: unknown[] }).values;
  return Array.isArray(values) && values.length > 0;
}

function responsiveSpec(spec: Record<string, unknown>): Record<string, unknown> {
  return {
    ...spec,
    width: "container",
    autosize: { type: "fit-x", contains: "padding" },
  };
}

export function VegaChart({ spec, title }: VegaChartProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !hasChartValues(spec)) return;

    let view: VegaView | undefined;
    let observer: ResizeObserver | undefined;
    let cancelled = false;

    void import("vega-embed").then(({ default: embed }) =>
      embed(el, responsiveSpec(spec), {
        actions: { export: true, source: false, compiled: false, editor: false },
        renderer: "svg",
      }).then((result) => {
        if (cancelled) {
          result.view.finalize();
          return;
        }
        view = result.view as VegaView;
        observer = new ResizeObserver(() => {
          void view?.resize().run();
        });
        observer.observe(el);
      }),
    );

    return () => {
      cancelled = true;
      observer?.disconnect();
      view?.finalize();
    };
  }, [spec]);

  if (!hasChartValues(spec)) {
    return <p className="text-xs text-stone-500">No chart data available.</p>;
  }

  return (
    <div
      ref={ref}
      className="w-full min-w-0 overflow-x-auto [&_svg]:mx-auto [&_svg]:max-w-full [&_svg]:h-auto"
      role="img"
      aria-label={title}
    />
  );
}
