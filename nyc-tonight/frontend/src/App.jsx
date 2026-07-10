import { useEffect, useRef, useState } from "react";
import { sendChat } from "./api.js";
import { ResultCard } from "./ResultCard.jsx";

const SUGGESTIONS = [
  "cheap dinner in Chinatown around 7pm",
  "something fun happening tonight near Williamsburg",
  "plan my night: dinner + a show in the East Village",
  "live music in Brooklyn this weekend",
];

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hey — I'm NYC Tonight. Tell me what you're in the mood for and I'll find restaurants or events. Try one of the suggestions below.",
      results: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function submit(text) {
    const message = (text ?? input).trim();
    if (!message || loading) return;

    setInput("");
    setError(null);
    const userMsg = { role: "user", content: message };
    const next = [...messages, userMsg];
    setMessages(next);
    setLoading(true);

    // Only send plain text turns as history (drop the greeting + card payloads).
    const history = next
      .slice(1)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const data = await sendChat(message, history.slice(0, -1));
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply_text || "Here's what I found.",
          results: data.results || [],
        },
      ]);
    } catch (err) {
      setError(err.message || "Something went wrong.");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I couldn't reach the server. Please try again.",
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

  const showSuggestions = messages.length <= 1;

  return (
    <div className="app">
      <header className="header">
        <h1>NYC Tonight</h1>
        <p>Restaurants &amp; events, found by an AI concierge.</p>
      </header>

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
              <span className="thinking-label">thinking…</span>
            </div>
          </div>
        )}

        {showSuggestions && !loading && (
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="chip" onClick={() => submit(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
      </main>

      {error && <div className="error-bar">{error}</div>}

      <footer className="composer">
        <textarea
          rows={1}
          value={input}
          placeholder="Ask for dinner, a show, or a whole night out…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
        />
        <button className="send" onClick={() => submit()} disabled={loading || !input.trim()}>
          Send
        </button>
      </footer>
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
