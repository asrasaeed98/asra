const API_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export async function sendChat(message, conversationHistory) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
    }),
  });
  if (!res.ok) {
    throw new Error(`Server error (${res.status})`);
  }
  return res.json();
}
