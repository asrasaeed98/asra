"""Periodic session progress updates so clients see activity during long work."""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timezone

from findings_api.db import get_session_factory
from findings_api.models import AnalysisSession

logger = logging.getLogger(__name__)

_TICKER_INTERVAL_SEC = 10.0
_ACTIVITY_SUFFIX = re.compile(r" · still working · (?:\d+m \d+s|\d+s)$")
_ACTIVE_STATUSES = frozenset({"ingesting", "analyzing"})


def strip_activity_suffix(message: str) -> str:
    """Remove the elapsed-time suffix added by the progress ticker."""
    return _ACTIVITY_SUFFIX.sub("", message).rstrip()


def format_activity_message(base: str, elapsed_sec: int) -> str:
    """Append a human-readable elapsed-time suffix to the current activity."""
    clean = strip_activity_suffix(base) or "Working on your analysis"
    if elapsed_sec >= 60:
        mins, secs = divmod(elapsed_sec, 60)
        elapsed = f"{mins}m {secs}s"
    else:
        elapsed = f"{elapsed_sec}s"
    return f"{clean} · still working · {elapsed}"


class ProgressTicker:
    """Background thread that refreshes session message and updated_at every 10s."""

    def __init__(self, session_id: str, *, interval_sec: float = _TICKER_INTERVAL_SEC) -> None:
        self.session_id = session_id
        self.interval_sec = interval_sec
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = datetime.now(timezone.utc)

    def __enter__(self) -> ProgressTicker:
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"progress-ticker-{self.session_id[:8]}",
        )
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval_sec + 2.0)

    def _elapsed_sec(self, now: datetime) -> int:
        return max(0, int((now - self._started_at).total_seconds()))

    def _tick(self) -> None:
        factory = get_session_factory()
        db = factory()
        try:
            session = db.get(AnalysisSession, self.session_id)
            if not session or session.status not in _ACTIVE_STATUSES:
                self._stop.set()
                return
            now = datetime.now(timezone.utc)
            base = strip_activity_suffix(session.message or "")
            # During active row-level download progress, only refresh updated_at.
            if session.phase == "ingest" and (
                "Downloaded" in base or "parallel" in base or "Downloading dataset" in base
            ):
                session.updated_at = now
            else:
                session.message = format_activity_message(
                    base or "Working on your analysis",
                    self._elapsed_sec(now),
                )
                session.updated_at = now
            db.add(session)
            db.commit()
        except Exception:
            logger.exception("Progress ticker failed for session %s", self.session_id)
        finally:
            db.close()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_sec):
            self._tick()
