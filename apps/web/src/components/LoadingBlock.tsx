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
      className={`flex ${minHeight} items-center justify-center rounded-2xl border border-[#e8ddd0] bg-[#faf8f5]/90 backdrop-blur-sm`}
    >
      <FunFindsLoader message={message} size="md" />
    </div>
  );
}
