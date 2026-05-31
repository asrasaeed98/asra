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

function responsiveSpec(
  spec: Record<string, unknown>,
  containerWidth: number,
): Record<string, unknown> {
  const isMobile = containerWidth > 0 && containerWidth < 640;
  const height = spec.height;
  const mobileHeight =
    typeof height === "number" ? Math.max(180, Math.round(height * 0.72)) : height;

  const baseConfig =
    spec.config && typeof spec.config === "object"
      ? (spec.config as Record<string, unknown>)
      : {};
  const axisConfig =
    baseConfig.axis && typeof baseConfig.axis === "object"
      ? (baseConfig.axis as Record<string, unknown>)
      : {};

  return {
    ...spec,
    width: "container",
    autosize: { type: "fit-x", contains: "padding" },
    ...(isMobile && typeof height === "number" ? { height: mobileHeight } : {}),
    config: {
      ...baseConfig,
      axis: {
        ...axisConfig,
        ...(isMobile
          ? {
              labelFontSize: 10,
              titleFontSize: 11,
              labelLimit: 72,
              titleLimit: 120,
            }
          : {}),
      },
    },
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
      embed(el, responsiveSpec(spec, el.clientWidth), {
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
      className="mx-auto w-full min-w-0 max-w-[18rem] overflow-x-auto sm:max-w-none [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      role="img"
      aria-label={title}
    />
  );
}
