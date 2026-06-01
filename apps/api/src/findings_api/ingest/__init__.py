def __getattr__(name: str):
    if name == "apply_session_config":
        from findings_api.ingest.pipeline import apply_session_config

        return apply_session_config
    if name == "run_ingest":
        from findings_api.ingest.pipeline import run_ingest

        return run_ingest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["apply_session_config", "run_ingest"]
