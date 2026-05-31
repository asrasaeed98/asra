#!/usr/bin/env python3
"""Copy catalog_resources from local API DB to production Postgres."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API / "src"))

from findings_api.config import settings  # noqa: E402
from findings_api.models import CatalogResource  # noqa: E402

BATCH = 500


def redact_url(url: str) -> str:
    return re.sub(r":([^:@/]+)@", ":***@", url.split("?")[0])


def prod_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    raise SystemExit(
        "Set DATABASE_URL to Railway DATABASE_PUBLIC_URL (or run via scripts/catalog-bootstrap-prod.sh)"
    )


def normalize(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


def main() -> None:
    local_url = settings.database_url
    prod_url = normalize(prod_database_url())
    local_engine = create_engine(local_url)
    prod_engine = create_engine(prod_url)

    with Session(local_engine) as local_sess:
        rows = list(local_sess.scalars(select(CatalogResource)).all())
    local_count = len(rows)
    print(f"local_db={redact_url(local_url)} local_rows={local_count}")

    with Session(prod_engine) as prod_sess:
        deleted = prod_sess.execute(delete(CatalogResource)).rowcount
        prod_sess.commit()
        print(f"prod_db={redact_url(prod_url)} cleared_rows={deleted or 0}")

        for i in range(0, local_count, BATCH):
            batch = rows[i : i + BATCH]
            for row in batch:
                prod_sess.merge(
                    CatalogResource(
                        id=row.id,
                        portal=row.portal,
                        title=row.title,
                        description=row.description,
                        organization=row.organization,
                        tags=row.tags,
                        format=row.format,
                        license_normalized=row.license_normalized,
                        license_raw=row.license_raw,
                        license_display=row.license_display,
                        attribution_required=row.attribution_required,
                        attribution_text=row.attribution_text,
                        publisher=row.publisher,
                        source_url=row.source_url,
                        resource_url=row.resource_url,
                        columns=row.columns,
                        row_count_hint=row.row_count_hint,
                        byte_size=row.byte_size,
                        ingestible=row.ingestible,
                        ingest_block_reason=row.ingest_block_reason,
                        detected_format=row.detected_format,
                        probed_at=row.probed_at,
                        updated_at=row.updated_at,
                        search_text=row.search_text,
                        synced_at=row.synced_at,
                    )
                )
            prod_sess.commit()
            print(f"copied {min(i + BATCH, local_count)}/{local_count}")

        prod_count = prod_sess.execute(
            text("SELECT COUNT(*) FROM catalog_resources")
        ).scalar()
    print(f"prod_rows={prod_count}")
    if prod_count != local_count:
        raise SystemExit(f"row mismatch: local={local_count} prod={prod_count}")


if __name__ == "__main__":
    main()
