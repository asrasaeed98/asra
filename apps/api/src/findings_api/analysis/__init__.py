def __getattr__(name: str):
    if name == "run_analysis_pipeline":
        from findings_api.analysis.runner import run_analysis_pipeline

        return run_analysis_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["run_analysis_pipeline"]
