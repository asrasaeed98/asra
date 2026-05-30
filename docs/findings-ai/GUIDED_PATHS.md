# Guided paths — product & build plan

> **Implemented (Slice 12a):** `paths.yaml`, `/guided/*` API, `/explore` UI (topic dropdown filter, compact pair cards), search quality ranking, home fork. Run catalog re-sync for new World Bank curated indicators.

## Goal

Offer **two entry points** for two audiences, sharing the same analysis engine (Review → Analyze → Results):

| Mode | User | Entry | Mental model |
|------|------|-------|--------------|
| **Guided** | Non-technical, question-first | “Ask a question” / topic tiles | “Help me answer something” |
| **Browse** | Comfortable with data, explorer | `/search` (existing) | “I know what datasets I want” |

Both paths converge at **dataset selection (1–2)** → **Review** → **Analyze** → **Results**. No duplicate analysis pipeline.

---

## Guided flow (target UX)

```text
Home or /explore
  → User asks a question OR picks a topic / starter path
  → App returns ranked dataset suggestions (+ optional pre-built pairs)
  → User picks 1–2 datasets (cart unchanged)
  → Review (intent pre-filled, join hints if pair recommended)
  → Analyze → Results (summary references their question)
```

Your assumption is correct: **question → find relevant datasets → user picks**. We add optional shortcuts (curated pairs, one-tap “use recommended pair”) without removing manual choice.

---

## Personas

### Guided user
- Has a plain-language question (“Does income relate to life expectancy?”)
- Does not know catalog names, portals, or join keys
- Needs confidence that the question is **answerable** before investing 2–4 minutes

### Browse user
- Searches by keyword, org, or known indicator
- Wants full catalog control, filters, and optional advanced Review settings
- May already know World Bank vs data.gov

---

## Information architecture

### Home (`/`)

Replace single CTA with a **fork** (not a forced choice):

```text
┌─────────────────────────────────────────────────────────┐
│  [ Ask a question ]          [ Browse datasets ]        │
│   Guided · best for most      Search · for explorers    │
└─────────────────────────────────────────────────────────┘
```

Keep existing “How it works” below; add one line: *Both paths use the same verified analysis engine.*

### New route: `/explore` (guided)

| Step | Screen | Purpose |
|------|--------|---------|
| 1 | Question input | Single-line input + inline example links |
| 2 | Suggestions | Ranked pairs (topic dropdown filter) + collapsed individual datasets |
| 3 | (existing) | `/review?ids=…&pair=…&intent=…` |

Browse stays at `/search` with no forced question step.

### Header nav (optional Phase 1)

- **Explore** → `/explore`
- **Search** → `/search`

---

## What we show after a question (Step 2)

Three blocks, top to bottom:

### A. Recommended pairs (when available)

Cards like:

> **Wealth and health across countries**  
> GDP per capita + Life expectancy at birth  
> Joins on country + year · ~17k rows · World Bank  
> [Use this pair]

Tapping pre-selects both IDs and skips to Review with `user_intent` and suggested `join_on`.

Source: **curated path registry** (JSON/YAML in repo for MVP; DB later).

### B. Individual datasets

Same card component as `/search`, ranked by question relevance, with a short **“Why this?”** line:

> Matches: *life expectancy*, *health*, *country*

### C. Honest limits

If the question is weak or unanswerable with the catalog:

> We didn’t find a strong match. Try rephrasing, pick a topic below, or [browse all datasets].

Never invent datasets or promise correlation before join validation.

---

## Ranking & matching (phased)

### Phase 1 — MVP (no LLM required)

**Curated paths registry** (`apps/api/src/findings_api/guided/paths.yaml` or similar):

```yaml
- id: wealth-health
  title: Wealth and health across countries
  question_patterns:
    - "life expectancy"
    - "wealth and health"
    - "gdp and health"
  user_intent: "Explore whether wealth and health outcomes move together across countries."
  resource_ids:
    - wb:NY.GDP.PCAP.CD
    - wb:SP.DYN.LE00.IN
  join_hint:
    - left: countryiso3code
      right: countryiso3code
    - left: date
      right: date
  topic: health
```

**Question → search:**

1. Tokenize question (stopwords removed)
2. Score catalog rows: title + tags + `search_text` token overlap (reuse search index)
3. Boost ingestible, CSV/JSON, row_count_hint, World Bank panels for macro questions
4. Match question against `question_patterns` on curated paths → surface pair at top if score ≥ threshold
5. Return `GET /guided/suggest?q=…` payload (see API below)

**Topic tiles** (empty / low-confidence state):

- Economy · Health · Education · Environment · US states  
- Each maps to 3–5 curated paths (not 8k search)

Launch with **8–12 curated paths** covering proven E2E pairs (GDP + life expectancy, electricity + clean fuels, etc.).

### Phase 2 — Query understanding (optional LLM)

Use Haiku **only** to:

- Expand question → search keywords + topic tags
- Map to nearest curated path id
- Generate 1-sentence `user_intent` paraphrase

**Guardrails:**

- LLM output cannot return resource IDs not in catalog
- Final dataset list always from deterministic search/ranking
- Log prompt + parsed tags; template fallback if API unavailable

### Phase 3 — Join-aware suggestions

When suggesting pairs:

- Run lightweight join **probe** on ingested sample (or cached join metadata from catalog sync)
- Badge: “Verified join” vs “Likely join — we’ll confirm on Review”

Depends on [join hygiene backlog](./BUILD_ORDER.md#slice-11--join-hygiene-phase-15-backlog) for normalization.

---

## API (new)

### `GET /guided/topics`

Returns topic tiles + path ids for empty state.

### `GET /guided/suggest`

| Param | Description |
|-------|-------------|
| `q` | User question (required, max ~500 chars) |
| `topic` | Optional topic slug from tile click |
| `limit` | Default 20 datasets, 3 pairs |

**Response:**

```json
{
  "query": "does wealth relate to life expectancy",
  "paraphrase": "Whether economic wealth and life expectancy are related across countries.",
  "recommended_pairs": [
    {
      "path_id": "wealth-health",
      "title": "Wealth and health across countries",
      "resource_ids": ["wb:NY.GDP.PCAP.CD", "wb:SP.DYN.LE00.IN"],
      "join_hint": [{"left": "countryiso3code", "right": "countryiso3code"}, {"left": "date", "right": "date"}],
      "confidence": "curated",
      "why": "Standard country-year indicators with a strong known relationship."
    }
  ],
  "datasets": [
    {
      "...CatalogResult fields...",
      "relevance_score": 0.82,
      "why": "Title and tags match life expectancy and GDP."
    }
  ],
  "fallback_message": null
}
```

### Reuse existing

- `GET /search` — unchanged for browse mode; optional `?intent=` boost later
- `POST /sessions` — pass `user_intent` from guided flow (already supported)
- `PATCH /sessions/{id}` — apply `join_on` from pair `join_hint`

---

## Web changes

| File / route | Change |
|--------------|--------|
| `app/page.tsx` | Two CTAs: Explore vs Search |
| `app/explore/page.tsx` | **New** — question input, topics, suggestions |
| `app/search/page.tsx` | Optional link “Not sure? Try guided explore”; starter collections (from SEARCH.md) |
| `app/review/page.tsx` | Read `intent` from query param; pre-apply join hint when `pair=` param present |
| `lib/api.ts` | `guidedSuggest()`, `guidedTopics()` |
| `layout.tsx` | Nav: Explore + Search |

**URL conventions:**

```text
/explore?q=does+wealth+relate+to+life+expectancy
/review?ids=wb:…,wb:…&intent=…&pair=wealth-health
/search?q=gdp                           # browse unchanged
```

---

## Curated path launch set (v1)

| Path id | Question it serves | Pair |
|---------|-------------------|------|
| `wealth-health` | Wealth vs longevity | GDP per capita + Life expectancy |
| `energy-access` | Electricity vs clean cooking | EG.ELC.ACCS.ZS + EG.CFT.ACCS.ZS |
| `us-states-health` | State health quality (single) | 2019 child/adult quality measures |
| `unemployment` | US labor market | FRED UNRATE (+ optional second FRED series) |
| `inflation` | Prices over time | FRED CPI (+ GDP optional) |
| `education-literacy` | Education outcomes | WB literacy + WB school enrollment |

Expand to ~12 paths before launch; all must pass E2E ingest + analysis smoke test.

---

## Phased delivery

### Slice 12a — Guided MVP (1–2 weeks)

- [ ] `paths.yaml` + loader + tests
- [ ] `GET /guided/suggest` (token overlap + path pattern match)
- [ ] `GET /guided/topics`
- [ ] `/explore` page (question + topics + results)
- [ ] Home fork UI
- [ ] Review: `intent` + `pair` query params → pre-fill intent & join hint
- [ ] 8–12 curated paths with smoke tests

**Out of scope for 12a:** LLM query expansion, join probe cache, one-click analyze without Review.

### Slice 12b — Polish (1 week)

- [ ] “Why this dataset?” strings on cards
- [ ] Starter collections on `/search` empty state (reuse path topics)
- [ ] Analytics: guided vs browse entry, path id usage, conversion to `complete`
- [ ] Low-confidence copy + topic fallback

### Slice 12c — Smarter matching (later)

- [ ] Haiku query expansion (guarded)
- [ ] Join-aware pair badges (with Slice 11 normalization)
- [ ] Re-rank search results when `user_intent` present on browse path too

---

## Trust & accuracy rules

1. **Curated paths are tested** — each path has a pytest or smoke script that runs ingest → join → analysis.
2. **Suggestions ≠ guarantees** — pair cards say “likely” until Review confirms join.
3. **LLM never picks datasets alone** (Phase 2+) — only keywords/tags; catalog search is source of truth.
4. **Same license gate** — guided mode only surfaces ingestible, allowlisted resources.
5. **`user_intent` stored on session** — flows into AI summary (already wired).

---

## Success metrics

| Metric | Target (8 weeks post-launch) |
|--------|--------------------------------|
| Guided sessions reaching `complete` | ≥ 50% of guided starts |
| Time to first dataset selection | < 90s (moderated) |
| Curated pair uptake | ≥ 30% of guided 2-dataset sessions use a recommended pair |
| Browse path unchanged | No regression in search → complete funnel |
| Support burden | Fewer “couldn’t join / didn’t know what to pick” outcomes (qualitative) |

---

## What we explicitly defer

- Full natural-language → auto-run without Review (users always confirm datasets + join)
- Semantic embedding search over 8k resources (until we have click data)
- User-authored paths / community collections
- Replacing `/search` — browse remains first-class

---

## Related docs

- [SEARCH.md](./SEARCH.md) — catalog search (browse path)
- [UX_FLOW.md](./UX_FLOW.md) — Review → Analyze → Results
- [BUILD_ORDER.md](./BUILD_ORDER.md) — Slice 12 checklist
- [HANDOFF.md](./HANDOFF.md) — backlog cross-links
