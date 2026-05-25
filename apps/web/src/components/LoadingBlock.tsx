import { FunFindsLoader } from "./FunFindsLoader";

type LoadingBlockProps = {
  message?: string;
  minHeight?: string;
};

export function LoadingBlock({
  message = "Loading…",
  minHeight = "min-h-[200px]",
}: LoadingBlockProps) {
  return (
    <div
      className={`flex ${minHeight} items-center justify-center rounded-2xl border border-pink-100 bg-white/80 backdrop-blur-sm`}
    >
      <FunFindsLoader message={message} size="md" />
    </div>
  );
}
