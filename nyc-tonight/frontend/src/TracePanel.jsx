/**
 * Flow matches backend/agent_loop.py:
 * Frontend → Backend → LLM → (tools on Backend) → LLM → Backend → Frontend
 */

function summarizeTurn(trace) {
  if (!trace?.rounds?.length) {
    return {
      tools: [],
      answered: false,
      toolSummaries: [],
      finalText: null,
      decideRound: null,
      answerRound: null,
    };
  }
  const tools = [];
  const toolSummaries = [];
  let answered = false;
  let decideRound = null;
  let answerRound = null;
  let finalText = null;

  for (const r of trace.rounds) {
    if ((r.tool_calls || []).length && r.stop_reason === "tool_use") {
      if (!decideRound) decideRound = r;
      for (const tc of r.tool_calls) {
        tools.push(tc.name);
        const result = (r.tool_results || []).find((tr) => tr.tool_use_id === tc.id);
        toolSummaries.push({
          name: tc.name,
          input: tc.input,
          summary: result?.summary,
          ok: result?.ok,
        });
      }
    }
    if (r.stop_reason === "end_turn" || (!r.tool_calls?.length && r.assistant_text)) {
      answered = true;
      answerRound = r;
      finalText = r.assistant_text || finalText;
    }
  }
  return { tools, answered, toolSummaries, finalText, decideRound, answerRound };
}

function Arrow() {
  return (
    <div className="flow-arrow" aria-hidden>
      <span className="flow-arrow-line" />
      <span className="flow-arrow-head">↓</span>
    </div>
  );
}

function IoBlock({ label, children, pending }) {
  return (
    <div className={`flow-io ${pending ? "pending" : ""}`}>
      <div className="flow-io-label">{label}</div>
      <div className="flow-io-body">{pending ? "…" : children}</div>
    </div>
  );
}

function prettyJson(value) {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return String(value);
  }
}

function clip(text, max = 160) {
  if (!text) return "…";
  const t = String(text).trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max)}…`;
}

export function TracePanel({ trace, loading, userMessage, replyText, resultCount }) {
  const hasTurn = Boolean(trace?.rounds?.length || trace?.error || loading || userMessage);
  const { tools, answered, toolSummaries, finalText } = summarizeTurn(trace);
  const usedTools = tools.length > 0;
  const reply = replyText || finalText;
  const toolNames = tools.map((t) => `\`${t}\``).join(", ");

  return (
    <aside className="trace-pane" aria-label="What's happening behind the scenes">
      <div className="trace-inner">
        <p className="notes-kicker">Behind the scenes</p>
        <h2>What’s happening</h2>

        {hasTurn && (
          <>
            <div className="roles-blurb">
              <p>
                <strong>Frontend</strong>: the chat UI. Sends your message; shows
                the reply.
              </p>
              <p>
                <strong>Backend</strong>: our server. Runs the loop and tools.
              </p>
              <p>
                <strong>LLM</strong>: the brain that decides. Picks tools and
                writes the answer.
              </p>
            </div>

            {loading && <div className="trace-status">Running the loop…</div>}
            {trace?.error && <div className="trace-error">{trace.error}</div>}

            {(trace?.provider || trace?.model) && (
              <p className="notes-meta">
                {trace.provider}
                {trace.model ? ` · ${trace.model}` : ""}
              </p>
            )}

            <div className="agent-flow" aria-label="Agent loop flow">
              <FlowNode who="Frontend" title="You ask" active>
                <IoBlock label="In" pending={!userMessage}>
                  Your typed message
                </IoBlock>
                <IoBlock label="Out" pending={!userMessage}>
                  <code className="flow-io-quote">{clip(userMessage, 120)}</code>
                  {" → backend"}
                </IoBlock>
              </FlowNode>

              <Arrow />

              <FlowNode who="Backend" title="Starts the loop" active>
                <IoBlock label="In" pending={!userMessage}>
                  User message + conversation history
                </IoBlock>
                <IoBlock label="Out" pending={loading && !trace?.rounds?.length}>
                  Message + tool list → LLM
                  <span className="flow-io-sub">
                    tools: search_restaurants, get_weather, search_events,
                    build_reservation_link
                  </span>
                </IoBlock>
              </FlowNode>

              <Arrow />

              <FlowNode who="LLM" title="The brain that decides" active accent="decide">
                <IoBlock label="In" pending={loading && !trace?.rounds?.length}>
                  Prompt + available tools
                </IoBlock>
                <IoBlock
                  label="Out"
                  pending={loading && !usedTools && !answered}
                >
                  {usedTools ? (
                    <>
                      Tool request: {renderInlineCode(toolNames)}
                      <span className="flow-io-sub">
                        (not a final answer yet)
                      </span>
                    </>
                  ) : answered ? (
                    "Final text answer (no tools)"
                  ) : (
                    "Waiting for decision…"
                  )}
                </IoBlock>
              </FlowNode>

              {(usedTools || (loading && !answered)) && (
                <>
                  <Arrow />
                  <FlowNode
                    who="Backend"
                    title="Runs tools"
                    active={usedTools || loading}
                    accent="act"
                  >
                    <IoBlock label="In" pending={!toolSummaries.length}>
                      {toolSummaries.length ? (
                        <ul className="flow-io-list">
                          {toolSummaries.map((t, i) => (
                            <li key={i}>
                              <code>{t.name}</code>
                              <pre>{prettyJson(t.input)}</pre>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        "Tool call(s) from the LLM"
                      )}
                    </IoBlock>
                    <IoBlock label="Out" pending={!toolSummaries.length}>
                      {toolSummaries.length ? (
                        <ul className="flow-io-list">
                          {toolSummaries.map((t, i) => (
                            <li key={i}>
                              <code>{t.name}</code>
                              {": "}
                              {t.summary || "done"}
                              {t.ok === false ? " (failed)" : ""}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        "Running…"
                      )}
                    </IoBlock>
                  </FlowNode>

                  <Arrow />

                  <FlowNode
                    who="LLM"
                    title="Reads results"
                    active={usedTools}
                    accent="observe"
                  >
                    <IoBlock label="In" pending={!toolSummaries.length}>
                      {toolSummaries.length
                        ? `Tool results (${toolSummaries.length}): ${toolSummaries
                            .map((t) => t.summary || t.name)
                            .join("; ")}`
                        : "Waiting for tool results…"}
                    </IoBlock>
                    <IoBlock label="Out" pending={!answered && loading}>
                      {answered
                        ? "Final reply text (grounded in tool data)"
                        : loading
                          ? "Writing an answer…"
                          : "May request another tool or answer"}
                    </IoBlock>
                  </FlowNode>
                </>
              )}

              <Arrow />

              <FlowNode
                who="Frontend"
                title="Shows the reply"
                active={answered}
                dim={!answered}
                accent="answer"
              >
                <IoBlock label="In" pending={!answered}>
                  {answered ? (
                    <>
                      <code className="flow-io-quote">{clip(reply, 140)}</code>
                      {resultCount > 0 && (
                        <span className="flow-io-sub">
                          + {resultCount} result card
                          {resultCount === 1 ? "" : "s"}
                        </span>
                      )}
                    </>
                  ) : (
                    "Reply + cards from backend"
                  )}
                </IoBlock>
                <IoBlock label="Out" pending={!answered}>
                  Rendered in chat (and this panel)
                </IoBlock>
              </FlowNode>
            </div>
          </>
        )}
      </div>
    </aside>
  );
}

function FlowNode({ who, title, active, dim, accent, children }) {
  const className = [
    "flow-node",
    active ? "active" : "",
    dim ? "dim" : "",
    accent ? `accent-${accent}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      <div className="flow-node-who">{who}</div>
      <div className="flow-node-title">{title}</div>
      <div className="flow-node-ios">{children}</div>
    </div>
  );
}

function renderInlineCode(text) {
  const parts = String(text).split(/(`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i}>{part.slice(1, -1)}</code>;
    }
    return <span key={i}>{part}</span>;
  });
}
