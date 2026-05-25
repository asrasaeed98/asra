# FunFinds — UI design decisions

## Principles

1. **Simple and effective** — one primary action per screen; minimal chrome.
2. **Warm and calm** — **beige/cream** surfaces; **pink** only as accent (not dominant).
3. **Feedback everywhere** — FunFinds loader on async waits.

## Color palette

### Primary (surfaces & chrome)

| Token | Hex | Use |
|-------|-----|-----|
| `cream-50` | `#faf8f5` | Page background |
| `cream-100` | `#f5efe6` | Cards, inputs, loader panels |
| `cream-200` | `#e8ddd0` | Borders, dividers |
| `cream-300` | `#ddd0c0` | Stronger borders |
| `stone-700` | `#44403c` | Body text |
| `stone-600` | `#57534e` | Secondary text |
| `stone-500` | `#78716c` | Muted text |

### Accent (pink — use sparingly)

| Token | Hex | Use |
|-------|-----|-----|
| `pink-500` | `#ec4899` | Primary CTA buttons, active step |
| `pink-600` | `#db2777` | CTA hover, links hover |
| `pink-400` | `#f472b6` | Bullets, labels, loader sparkles |
| `pink-100` | `#fce7f3` | Attribution badges, AI summary tint |

**Do not:** pink page backgrounds, pink headers, or pink card fills.

## Typography

- **Font:** Geist Sans
- **Headings:** `text-stone-800`; accent word `text-pink-600` optional
- **Body:** `text-stone-600` / `text-stone-500`

## Components

| Component | Style |
|-----------|--------|
| **Header** | `bg-white/90`, `border-cream-200`, logo `text-stone-800` with pink accent optional |
| **Primary button** | `bg-pink-600` (accent action on cream page) |
| **Secondary button** | `bg-cream-100` `border-cream-300` `text-stone-700` |
| **Card** | `bg-white` or `bg-cream-50`, `border-cream-200` |
| **Input** | `bg-white`, `border-cream-300`, focus `ring-pink-200` |
| **AI summary** | `bg-cream-50`, `border-cream-200`, title `text-pink-800` |

## Loading

- `FunFindsLoader` — mascot uses cream/pink (not all-pink blob on pink bg)
- Optional `public/funfinds-loader.gif`

## Accessibility

- Pink CTAs: white text on `pink-600` (accent only, small areas)
