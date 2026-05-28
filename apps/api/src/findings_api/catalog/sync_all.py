from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from findings_api.catalog.sync_datagov import sync_datagov
from findings_api.catalog.sync_worldbank import sync_worldbank


async def run_full_sync(session: Session) -> dict[str, int]:
    # Avoid system HTTP proxies breaking local dev sync (common ProxyError 403).
    async with httpx.AsyncClient(follow_redirects=True, trust_env=False) as client:
        dg_n = await sync_datagov(session, client)
        wb_n = await sync_worldbank(session, client)
        from findings_api.catalog.sync_fred import sync_fred

        fred_n = await sync_fred(session, client)
    return {"data_gov": dg_n, "world_bank": wb_n, "fred": fred_n}
