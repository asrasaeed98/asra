# TokenTrim — vision

**Status:** Early scaffold in `apps/tokentrim`. **Name: TokenTrim.** Positioning: token efficiency.

## One-liner

**Same intent. Fewer tokens.** Paste a bloated prompt, get three lean rewrites, pick the one that cuts your API bill.

## North star

**Token efficiency is the face of the app.** Every feature answers: *"How does this help me say the same thing with fewer tokens?"*

## Problem

Vague words, repetition, and filler cost money at scale. Most prompt tools optimize for quality, not token count — users still ship 400-token prompts when 120 would work.

## Solution

Three copy-ready rewrites, each a different compression strategy:

| Variant | Token strategy |
|---------|----------------|
| **Concise** | Aggressive trim — minimum tokens, same intent |
| **Structured** | Efficient scaffolding — sections only where they earn tokens |
| **Context-aware** | Context stated once, tightly — no repeated blocks |

Each variant explains **why it's shorter** so users learn lean writing.

---

## Primary audience

**Developers & builders** who pay per token — API users, agent builders, production prompt workflows.

**Messages:**
1. *Same intent. Fewer tokens.* (hero)
2. *Three lean rewrites. Copy. Ship.* (mechanic)
3. *Lower API bills without dumbing down your intent.* (proof)

**Portfolio:** Findings = data → insight. TokenTrim = intent → instruction, efficiently.

---

## Brand

| | |
|---|---|
| **Name** | TokenTrim |
| **Tagline** | Same intent. Fewer tokens. |
| **Domain** | TBD (tokentrim.com, tokentrim.app, etc.) |

---

## Roadmap (token-facing)

- [ ] Before/after token estimate per variant
- [ ] Highlight removed filler (diff view)
- [ ] Savings at scale (e.g. cost at 1k runs/month)
- [ ] Deploy strategy

---

## Repo layout

```
apps/tokentrim/     # Next.js app
docs/tokentrim/     # This file
```
