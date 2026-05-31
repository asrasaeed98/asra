import type { CatalogResult } from "@/lib/api";
import { portalLabel } from "@/lib/catalog-labels";

export function SourceAttributions({ catalogs }: { catalogs: CatalogResult[] }) {
  if (catalogs.length === 0) return null;

  return (
    <section className="mt-8 rounded-xl border border-[#e8ddd0] bg-[#faf8f5] p-4 sm:p-5">
      <h2 className="text-sm font-semibold text-stone-800">Data sources & attribution</h2>
      <p className="mt-1 text-xs text-stone-500">
        Cite these sources when sharing or publishing results from this analysis.
      </p>
      <ul className="mt-3 space-y-3">
        {catalogs.map((item) => (
          <li key={item.id} className="text-sm leading-relaxed text-stone-700">
            <p className="font-medium text-stone-800">{item.title}</p>
            <p className="mt-0.5 text-xs text-stone-500">
              {portalLabel(item.portal)}
              {item.license_display ? ` · ${item.license_display}` : null}
            </p>
            {item.attribution_text && (
              <p className="mt-1 text-xs text-stone-600">{item.attribution_text}</p>
            )}
            {item.source_url && (
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-block text-xs font-medium text-pink-600 hover:text-pink-700"
              >
                View source dataset →
              </a>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
