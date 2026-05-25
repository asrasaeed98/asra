# Search — catalog-backed discovery

## Approach

Search a **local PostgreSQL index** fed by CKAN sync — not live API per keystroke.

## MVP features

1. Full-text search (title, description, org, tags)
2. Facets: tags, organization, format (CSV/JSON default), updated
3. Sort: relevance, recently updated, title
4. Result cards: license badge, format, size estimate
5. Preview drawer: columns, link to source
6. Selection cart: max 2 datasets
7. Starter collections on empty state (Economy, Health, Environment)

## Optional intent box

Re-ranks results via tag/title token overlap — does not change license rules.

## Ranking signals

| Signal | Weight |
|--------|--------|
| Title match | High |
| Tag match | High |
| Description | Medium |
| CSV/JSON format | Boost |
| Recent update | Small boost |
| File over ROW_CAP | Penalize or badge |

## API

`GET /search?q=&tags=&org=&format=&sort=&page=`

## Success metrics

- User finds relevant dataset in < 60s (moderated test)
- Zero non-allowlisted rows in index
