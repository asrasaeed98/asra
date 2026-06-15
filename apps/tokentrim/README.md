# TokenTrim

> **Same intent. Fewer tokens.**  
> **Status:** Early scaffold. See [docs/tokentrim/VISION.md](../../docs/tokentrim/VISION.md).

## Intent

Users paste a verbose prompt → app returns **three token-efficient rewrites**, each using a different compression strategy. Future: before/after token counts.

## Layout

```
apps/tokentrim/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main UI (WIP)
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── api/refine/       # Server-side refinement endpoint
│   └── lib/
│       ├── refine.ts         # System prompt + Anthropic call
│       └── types.ts
├── package.json
└── README.md                 # This file
```

## Local dev

Port **3001** (Findings uses 3000).

```bash
# From repo root
npm run dev:tokentrim
```

Requires `ANTHROPIC_API_KEY` in root `.env`.

## Next steps (product)

- Before/after token count per variant
- UI polish and savings-at-scale display
- Deploy (separate Vercel project or subdomain)
