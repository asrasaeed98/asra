import asyncio
from unittest.mock import MagicMock, patch

import pytest

from findings_api.ingest.pipeline import _ParallelDownloadProgress, _download_resource
from findings_api.models import AnalysisSession, CatalogResource


@pytest.fixture
def wb_resources():
    return [
        CatalogResource(
            id="wb:1",
            portal="world_bank",
            title="GDP per capita",
            description=None,
            organization="WB",
            tags=[],
            format="JSON",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="attr",
            publisher="WB",
            source_url="https://wb/1",
            resource_url="https://api.worldbank.org/v2/country/all/indicator/1",
            search_text="gdp",
        ),
        CatalogResource(
            id="wb:2",
            portal="world_bank",
            title="Greenhouse gas emissions",
            description=None,
            organization="WB",
            tags=[],
            format="JSON",
            license_normalized="CC_BY",
            license_raw="CC-BY",
            license_display="CC BY",
            attribution_required=True,
            attribution_text="attr",
            publisher="WB",
            source_url="https://wb/2",
            resource_url="https://api.worldbank.org/v2/country/all/indicator/2",
            search_text="ghg",
        ),
    ]


def test_parallel_download_progress_message():
    db = MagicMock()
    session = AnalysisSession(
        id="s1",
        status="ingesting",
        phase="ingest",
        resource_ids=["wb:1", "wb:2"],
    )
    db.get.return_value = session
    tracker = _ParallelDownloadProgress(db, "s1", resources=[MagicMock(title="A"), MagicMock(title="B")])
    msg = tracker._compose_message(0, "Downloaded 1,000 of 2,000 rows (50%)…")
    assert "parallel" in msg
    assert "0/2 fetched" in msg


def test_download_resources_run_in_parallel(wb_resources):
    import time

    call_times: list[float] = []

    async def slow_fetch(*args, **kwargs):
        call_times.append(time.monotonic())
        await asyncio.sleep(0.05)
        return (b"[]", "json")

    async def run():
        db = MagicMock()
        session = AnalysisSession(
            id="s1",
            status="ingesting",
            phase="ingest",
            resource_ids=["wb:1", "wb:2"],
        )
        db.get.return_value = session
        progress = _ParallelDownloadProgress(db, "s1", resources=wb_resources)
        client = MagicMock()

        with patch("findings_api.ingest.pipeline.fetch_resource_bytes", new=slow_fetch):
            start = time.monotonic()
            results = await asyncio.gather(
                _download_resource(0, wb_resources[0], client=client, progress=progress, total_n=2),
                _download_resource(1, wb_resources[1], client=client, progress=progress, total_n=2),
            )
            elapsed = time.monotonic() - start

        assert len(results) == 2
        assert elapsed < 0.12
        assert len(call_times) == 2
        assert abs(call_times[0] - call_times[1]) < 0.03

    asyncio.run(run())
