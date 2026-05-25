# Costs — ~100 users (prototype)

## Anthropic (Sonnet $3/$15, Haiku $1/$5 per MTok — verify current pricing)

| Scenario | Sessions/mo | Est. API $/mo |
|----------|-------------|---------------|
| Soft launch (30 active × 2 runs) | 60 | $6–10 |
| Moderate (50 × 3 runs, 8 chats) | 150 | $18–35 |
| Energetic (100 × 2 runs, 10 chats) | 200 | $25–55 |

**Per session (typical):** ~$0.10 (summary + 5 chats).

**$5 test credit:** ~20–50 full sessions.

**Budget recommendation:** $50–100/mo prepaid + billing alerts at $25, $50.

## Infra

| Item | $/mo |
|------|------|
| Vercel + API host + Postgres + Redis | $15–70 |

**All-in casual 100 users:** ~$45–120/mo.

## Controls

- Haiku for summary, Sonnet for chat
- Prompt caching for schema in chat
- Rate limits per session/user
- Truncate chat history
