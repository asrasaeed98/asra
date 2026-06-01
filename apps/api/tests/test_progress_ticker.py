from findings_api.progress_ticker import format_activity_message, strip_activity_suffix


def test_strip_activity_suffix():
    assert strip_activity_suffix("Downloading dataset · still working · 45s") == "Downloading dataset"
    assert strip_activity_suffix("Running ML · still working · 2m 10s") == "Running ML"


def test_format_activity_message_seconds():
    assert format_activity_message("Downloading dataset", 8) == "Downloading dataset · still working · 8s"


def test_format_activity_message_minutes():
    assert format_activity_message("Running analysis", 130) == "Running analysis · still working · 2m 10s"


def test_format_activity_message_strips_existing_suffix():
    msg = format_activity_message("Downloading · still working · 10s", 25)
    assert msg == "Downloading · still working · 25s"
