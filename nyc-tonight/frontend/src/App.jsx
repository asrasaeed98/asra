import { useEffect, useMemo, useRef, useState } from "react";
import { fetchHealth, sendChat } from "./api.js";
import { ResultCard } from "./ResultCard.jsx";
import { LessonNotes } from "./LessonNotes.jsx";
import { TracePanel } from "./TracePanel.jsx";
import {
  LESSONS,
  LESSON1_PROMPTS,
  buildLesson1Sections,
  lesson1Step,
} from "./lessons.js";

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeLesson, setActiveLesson] = useState("lesson-1");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hey, I'm NYC Tonight. Ask me about dinner, weather, or something fun tonight. Notes on the left teach agent basics; the right panel shows the loop behind the scenes.",
      results: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [latestTrace, setLatestTrace] = useState(null);
  const [userTurns, setUserTurns] = useState(0);
  const [health, setHealth] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    fetchHealth().then(setHealth);
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const step = lesson1Step({ userTurns, latestTrace });
  const notes = useMemo(
    () => buildLesson1Sections({ step, latestTrace }),
    [step, latestTrace]
  );

  async function submit(text) {
    const message = (text ?? input).trim();
    if (!message || loading) return;

    setInput("");
    setError(null);
    const userMsg = { role: "user", content: message };
    const next = [...messages, userMsg];
    setMessages(next);
    setLoading(true);

    const history = next
      .slice(1)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const data = await sendChat(message, history.slice(0, -1));
      setUserTurns((n) => n + 1);
      setLatestTrace(data.trace || null);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply_text || "Here's what I found.",
          results: data.results || [],
        },
      ]);
      if (data.trace?.provider) {
        setHealth((h) =>
          h
            ? { ...h, provider: data.trace.provider, model: data.trace.model }
            : h
        );
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I couldn't reach the server. Is the backend running on port 8000?",
          results: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const statusLabel = health
    ? `${health.provider || "…"}${health.model ? ` · ${health.model}` : ""}`
    : "connecting…";

  const showSuggestions = userTurns === 0 && !loading;

  const lastUserMessage = [...messages].reverse().find((m) => m.role === "user");
  const lastAssistant =
    messages.length > 1 && messages[messages.length - 1].role === "assistant"
      ? messages[messages.length - 1]
      : null;

  return (
    <div className="lab">
      <header className="lab-header">
        <button
          type="button"
          className={menuOpen ? "menu-btn open" : "menu-btn"}
          aria-label={menuOpen ? "Close lessons" : "Open lessons"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span className="menu-icon" aria-hidden>
            <span />
            <span />
            <span />
          </span>
        </button>
        <div className="lab-brand">
          <h1>Agent Lab</h1>
          <p>Learn agents with NYC Tonight</p>
        </div>
        <div className="lab-status" title="Active model provider">
          {statusLabel}
        </div>
      </header>

      {menuOpen && (
        <button
          type="button"
          className="menu-backdrop"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <nav
        className={menuOpen ? "lesson-drawer open" : "lesson-drawer"}
        aria-label="Lessons"
        aria-hidden={!menuOpen}
      >
        <h2>Lessons</h2>
        <ul>
          {LESSONS.map((l) => (
            <li key={l.id}>
              <button
                type="button"
                className={
                  activeLesson === l.id ? "lesson-item active" : "lesson-item"
                }
                disabled={!l.available}
                tabIndex={menuOpen ? 0 : -1}
                onClick={() => {
                  if (!l.available) return;
                  setActiveLesson(l.id);
                  setMenuOpen(false);
                }}
              >
                <span className="lesson-num">{l.number}</span>
                <span>
                  {l.title}
                  {!l.available && (
                    <span className="coming-soon"> Coming soon</span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="lab-body">
        <LessonNotes notes={notes} onTryPrompt={submit} loading={loading} />

        <section className="chat-pane" aria-label="Chat with the agent">
          <main className="messages" ref={listRef}>
            {messages.map((m, i) => (
              <Message key={i} message={m} />
            ))}

            {loading && (
              <div className="msg assistant">
                <div className="bubble thinking">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                  <span className="thinking-label">working…</span>
                </div>
              </div>
            )}

            {showSuggestions && (
              <div className="suggestions">
                <button
                  className="chip"
                  onClick={() => submit(LESSON1_PROMPTS.first)}
                >
                  {LESSON1_PROMPTS.first}
                </button>
                <button
                  className="chip"
                  onClick={() => submit(LESSON1_PROMPTS.second)}
                >
                  {LESSON1_PROMPTS.second}
                </button>
              </div>
            )}
          </main>

          {error && <div className="error-bar">{error}</div>}

          <footer className="composer">
            <textarea
              rows={1}
              value={input}
              placeholder="Ask the agent…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={loading}
            />
            <button
              className="send"
              onClick={() => submit()}
              disabled={loading || !input.trim()}
            >
              Send
            </button>
          </footer>
        </section>

        <TracePanel
          trace={loading ? null : latestTrace}
          loading={loading}
          userMessage={lastUserMessage?.content || null}
          replyText={loading ? null : lastAssistant?.content || null}
          resultCount={loading ? 0 : (lastAssistant?.results || []).length}
        />
      </div>
    </div>
  );
}

function Message({ message }) {
  const isUser = message.role === "user";
  const results = message.results || [];
  return (
    <div className={`msg ${isUser ? "user" : "assistant"}`}>
      <div className="bubble">{message.content}</div>
      {results.length > 0 && (
        <div className="cards">
          {results.map((r, i) => (
            <ResultCard key={i} result={r} />
          ))}
        </div>
      )}
    </div>
  );
}
