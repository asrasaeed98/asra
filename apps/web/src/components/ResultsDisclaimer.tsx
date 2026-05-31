import { APP_NAME } from "@/lib/app-name";

export function ResultsDisclaimer() {
  return (
    <section
      className="mt-8 rounded-xl border border-amber-100 bg-amber-50/60 p-4 sm:p-5"
      aria-label="Important limitations"
    >
      <h2 className="text-sm font-semibold text-amber-950">Important limitations</h2>
      <ul className="mt-2 list-disc space-y-1.5 pl-5 text-xs leading-relaxed text-amber-950/90">
        <li>
          Results are based on the datasets and sample used. Public data may contain errors,
          missing values, or outdated records.
        </li>
        <li>
          Statistical patterns show association, not causation. Verify important conclusions
          against the underlying data and source documentation.
        </li>
        <li>
          AI summaries and chat answers explain computed results. Detailed result cards and the
          analysis report are the authoritative numbers.
        </li>
        <li>
          {APP_NAME} does not provide financial, medical, legal, or policy advice. Do not rely on
          this tool as your sole basis for high-stakes decisions.
        </li>
      </ul>
    </section>
  );
}
