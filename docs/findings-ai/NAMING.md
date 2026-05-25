# App naming

## Your ideas

| Name | Pros | Cons |
|------|------|------|
| **FunFinds** | Clear (open data + findings), trustworthy tone | `.com` may be taken |
| **FunFinds** | Memorable, friendly | Sounds less serious for stats/trust |
| **Findings.ai** | Professional, outcome-focused | `.ai` domains cost more |

## Recommendation

**Primary: FunFinds** — best balance of clarity and approachability for a public-data prototype.

**Runner-up: Findings.ai** — if you want a more “product / AI” brand later.

**FunFinds** — good for consumer marketing; consider as tagline (“FunFinds by FunFinds”) rather than legal product name.

## Implementation

Set display name via environment:

```bash
NEXT_PUBLIC_APP_NAME=FunFinds
```

Code falls back to `FunFinds` until you finalize branding.
