# Data sources — Phase 1

## Primary portal: data.gov (CKAN)

- **API base:** `https://catalog.data.gov/api/3/action`
- **Actions:** `package_search`, `package_show`
- **Per resource:** `url`, `format`, `size`, license on package/resource

## Phase 1 optional second portal

- **World Bank Open Data API** — clean indicator metadata, good for demos

## License fields (CKAN)

Map to internal enum:

| Raw signals | `license_normalized` | Ingest |
|-------------|----------------------|--------|
| CC0, CCZero | `CC0` | Allow |
| US Public Domain, us-pd | `US_PD` | Allow |
| US Government Work | `US_GOV_WORK` | Allow |
| Missing, other, CC-BY, ODbL, NC | — | **Reject** |

## Index document (per resource)

```json
{
  "id": "ckan:{package_id}:{resource_id}",
  "title": "",
  "description": "",
  "organization": "",
  "tags": [],
  "format": "CSV",
  "license_normalized": "CC0",
  "source_url": "",
  "columns": [],
  "byte_size": null,
  "updated_at": ""
}
```

## Sync schedule

- Nightly full/incremental sync
- HEAD or metadata size for large-file warnings in UI

## Not in Phase 1

- Kaggle, Hugging Face, arbitrary URLs, PDF-only resources (hidden by default in search)
