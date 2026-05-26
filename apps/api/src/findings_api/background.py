"""Run blocking session work off the FastAPI event loop."""

from __future__ import annotations

import threading
from typing import Callable


def run_in_background(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, daemon=True, name="findings-worker").start()
