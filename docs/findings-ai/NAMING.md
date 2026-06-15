# App naming

## Chosen name

**Findings** — live at [findings.site](https://www.findings.site).

Clear, outcome-focused, and professional for a public-data analysis product.

## Alternatives considered

| Name | Pros | Cons |
|------|------|------|
| **Findings** | Professional, outcome-focused | Generic word |
| **Findings.ai** | Strong “product / AI” brand | `.ai` domains cost more |
| **FunFinds** | Memorable, friendly | Sounds less serious for stats/trust |

## Implementation

Display name is set via environment:

```bash
NEXT_PUBLIC_APP_NAME=Findings
```

Code falls back to `Findings` when unset.
