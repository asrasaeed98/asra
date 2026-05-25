# App naming

## Your ideas

| Name | Pros | Cons |
|------|------|------|
| **OpenFinds** | Clear (open data + findings), trustworthy tone | `.com` may be taken |
| **FunFinds** | Memorable, friendly | Sounds less serious for stats/trust |
| **Findings.ai** | Professional, outcome-focused | `.ai` domains cost more |

## Recommendation

**Primary: OpenFinds** — best balance of clarity and approachability for a public-data prototype.

**Runner-up: Findings.ai** — if you want a more “product / AI” brand later.

**FunFinds** — good for consumer marketing; consider as tagline (“FunFinds by OpenFinds”) rather than legal product name.

## Implementation

Set display name via environment:

```bash
NEXT_PUBLIC_APP_NAME=OpenFinds
```

Code falls back to `OpenFinds` until you finalize branding.
