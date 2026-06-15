import { FindingsLoader } from "./FindingsLoader";

type LoadingBlockProps = {
  message?: string;
  minHeight?: string;
  percent?: number;
  timeHint?: string;
  activityHint?: string;
  stuckHint?: string;
};

export function LoadingBlock({
  message = "Loading…",
  minHeight = "min-h-[200px]",
  percent,
  timeHint,
  activityHint,
  stuckHint,
}: LoadingBlockProps) {
  const showBar = percent != null && percent >= 0;

  return (
    <div
      className={`flex ${minHeight} flex-col items-center justify-center rounded-2xl border border-[#e8ddd0] bg-[#faf8f5]/90 px-6 py-8 backdrop-blur-sm`}
    >
      <FindingsLoader message={message} size="md" />
      {showBar && (
        <div className="mt-6 w-full max-w-xs">
          <div className="h-2 overflow-hidden rounded-full bg-[#e8ddd0]">
            <div
              className="h-full rounded-full bg-pink-500 transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
            />
          </div>
          <p className="mt-2 text-center text-xs text-stone-500">{percent}% complete</p>
        </div>
      )}
      {timeHint && <p className="mt-2 text-center text-xs text-stone-400">{timeHint}</p>}
      {activityHint && (
        <p className="mt-2 text-center text-xs text-stone-500">{activityHint}</p>
      )}
      {stuckHint && (
        <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-center text-xs text-amber-900">
          {stuckHint}
        </p>
      )}
    </div>
  );
}

function formatSeconds(sec?: number | null): string | undefined {
  if (sec == null || sec <= 0) return undefined;
  if (sec < 60) return `About ${sec} sec left`;
  const mins = Math.ceil(sec / 60);
  return mins === 1 ? "About 1 min left" : `About ${mins} min left`;
}

export { formatSeconds };
