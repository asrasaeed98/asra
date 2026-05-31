"use client";

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { sendSessionChat, type ChatState, type ChatTurn } from "@/lib/api";

const SUGGESTIONS = [
  "What's the most important finding?",
  "What does this mean in plain terms?",
  "Which fields were most related?",
];

const assistantMarkdownComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="mb-2 last:mb-0">{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold text-stone-800">{children}</strong>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="my-2 list-disc space-y-1 pl-4">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="my-2 list-decimal space-y-1 pl-4">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => <li>{children}</li>,
};

export function ChatPanel({
  sessionId,
  initial,
}: {
  sessionId: string;
  initial?: ChatState;
}) {
  const maxQuestions = initial?.max_questions ?? 5;
  const [messages, setMessages] = useState<ChatTurn[]>(initial?.messages ?? []);
  const [remaining, setRemaining] = useState<number>(
    initial?.questions_remaining ?? maxQuestions,
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiPaused, setAiPaused] = useState<boolean>(initial?.ai_paused ?? false);
  const listRef = useRef<HTMLDivElement>(null);

  const limitReached = remaining <= 0;
  const disabled = limitReached || aiPaused;
  const canSend = !loading && !disabled && input.trim().length > 0;

  async function ask(question: string) {
    const text = question.trim();
    if (!text || loading || disabled) return;
    setError(null);
    setLoading(true);
    setInput("");
    const prevLen = messages.length;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    try {
      const res = await sendSessionChat(sessionId, text);
      setRemaining(res.questions_remaining);
      setAiPaused(res.ai_paused ?? false);
      const persisted = res.messages.length > prevLen;
      setMessages(res.messages);
      if (!persisted) {
        // Budget/error: the turn wasn't counted — surface the reply as a notice.
        setError(res.reply);
        setInput(text);
      }
      requestAnimationFrame(() => {
        listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
      });
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not reach the chat service. Try again.",
      );
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-[#e8ddd0] bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-stone-800">Ask about these results</h2>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
            limitReached
              ? "bg-stone-200 text-stone-500"
              : "bg-pink-100 text-pink-800"
          }`}
        >
          {remaining} of {maxQuestions} questions left
        </span>
      </div>
      <p className="mt-1 text-xs text-stone-500">
        Answers use your findings and can query loaded session data for specifics. Limited to{" "}
        {maxQuestions} questions.
      </p>

      {aiPaused && (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          The AI assistant is paused — we&apos;ve hit the monthly usage budget. It&apos;ll come back
          when the limit resets. Your results above are unaffected.
        </p>
      )}

      {messages.length > 0 && (
        <div
          ref={listRef}
          className="mt-4 max-h-80 space-y-3 overflow-y-auto rounded-lg border border-[#f0e8de] bg-[#faf8f5] p-3"
        >
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "whitespace-pre-wrap bg-pink-600 text-white"
                    : "border border-[#e8ddd0] bg-white text-stone-700"
                }`}
              >
                {m.role === "user" ? (
                  m.content
                ) : (
                  <ReactMarkdown components={assistantMarkdownComponents}>{m.content}</ReactMarkdown>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <p className="rounded-2xl border border-[#e8ddd0] bg-white px-3 py-2 text-sm text-stone-400">
                Thinking…
              </p>
            </div>
          )}
        </div>
      )}

      {messages.length === 0 && !disabled && (
        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => ask(s)}
              disabled={loading}
              className="rounded-full border border-[#e8ddd0] bg-[#faf8f5] px-3 py-1.5 text-xs text-stone-600 transition hover:border-pink-300 hover:text-pink-700 disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p className="mt-3 rounded-lg border border-pink-200 bg-pink-50 px-3 py-2 text-xs text-pink-900">
          {error}
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="mt-4 flex flex-col gap-2 sm:flex-row"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading || disabled}
          maxLength={2000}
          placeholder={
            aiPaused
              ? "AI assistant is paused (usage limit reached)"
              : limitReached
                ? "Question limit reached for this analysis"
                : "Ask a question…"
          }
          className="flex-1 rounded-xl border border-[#ddd0c0] bg-white px-3 py-2.5 text-sm text-stone-800 focus:border-pink-300 focus:outline-none focus:ring-2 focus:ring-pink-100 disabled:bg-[#faf8f5] disabled:text-stone-400"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="w-full rounded-xl bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-50 hover:bg-pink-700 sm:w-auto"
        >
          {loading ? "…" : "Ask"}
        </button>
      </form>

      {limitReached && (
        <p className="mt-2 text-xs text-stone-500">
          You&apos;ve used all {maxQuestions} questions.{" "}
          <a href="/search" className="font-medium text-pink-600 hover:text-pink-700">
            Start a new analysis
          </a>{" "}
          to ask more.
        </p>
      )}
    </section>
  );
}
