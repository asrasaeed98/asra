# FunFinds — UI design decisions

## Principles

1. **Simple and effective** — one primary action per screen; minimal chrome.
2. **Friendly trust** — soft pink palette feels approachable; computed results stay clear and readable.
3. **Feedback everywhere** — loading always shows the FunFinds loader (gif or animated mascot).

## Color palette (pink-ish)

| Token | Hex | Use |
|-------|-----|-----|
| `pink-50` | `#fdf2f8` | Page background gradient start |
| `pink-100` | `#fce7f3` | Cards, subtle fills |
| `pink-200` | `#fbcfe8` | Borders, hover |
| `pink-500` | `#ec4899` | Primary buttons, links |
| `pink-600` | `#db2777` | Primary button hover |
| `pink-700` | `#be185d` | Headings accent |
| `rose-400` | `#fb7185` | Secondary highlights |
| `slate-700` | `#334155` | Body text |
| `slate-500` | `#64748b` | Muted text |

**Avoid:** harsh pure black, neon greens (old prototype). **AI summary** block uses soft violet-pink (`pink-100` + border `pink-200`), not generic purple.

## Typography

- **Font:** Geist Sans (already in Next.js).
- **Headings:** semibold, `text-zinc-800` / `pink-700` for H1 accent word.
- **Body:** `text-sm` / `text-base`, `text-slate-600`.

## Layout

- Max width `max-w-3xl` for wizard steps; `max-w-5xl` for header.
- Generous padding `px-4 py-10`.
- Rounded corners `rounded-xl` on cards and buttons.

## Components

| Component | When |
|-----------|------|
| `FunFindsLoader` | Any async wait > 300ms (search, analyze, results load) |
| `LoadingBlock` | Full-section placeholder with message |
| `Button` primary | Pink-600, white text |
| `Card` | White bg, `border-pink-100`, light shadow |

## Loading / “cute gif”

1. **Default:** animated SVG mascot in `FunFindsLoader` (bouncing blob + sparkles) — no external deps.
2. **Optional:** place `public/funfinds-loader.gif` — component prefers gif if file exists (checked client-side or static path).

Use loader on:

- Search submit
- Analyze progress (beside or above step list)
- Results initial fetch
- Future: chat “thinking”

## Wizard steps (visual)

1. **Home** — hero, one CTA “Search datasets”
2. **Search** — search bar + portal filter + result cards
3. **Review** — summary list, filters (slice 3), pink CTA “Run analysis”
4. **Analyze** — loader + stepper
5. **Results** — AI summary card → computed findings → charts → chat

## Accessibility

- Loader includes `role="status"` and `aria-live="polite"`.
- Pink buttons maintain contrast ratio ≥ 4.5:1 (white on pink-600).

## Not in Phase 1 UI

- Dark mode
- Complex dashboard / side nav
- Custom illustration set beyond loader
