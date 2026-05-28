from findings_api.catalog.sync_limits import max_indexed, should_probe
from findings_api.config import settings


def test_max_indexed_defaults_to_ingestible_cap():
    assert max_indexed(200, 0) == 200
    assert max_indexed(200, 500) == 500


def test_should_probe_respects_cap_and_setting(monkeypatch):
    monkeypatch.setattr(settings, "catalog_probe_enabled", True)
    assert should_probe(ingestible=0, ingestible_cap=200) is True
    assert should_probe(ingestible=200, ingestible_cap=200) is False
    monkeypatch.setattr(settings, "catalog_probe_enabled", False)
    assert should_probe(ingestible=0, ingestible_cap=200) is False
