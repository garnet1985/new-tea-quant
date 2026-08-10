"""Background drain for long-lived BFF process."""

from __future__ import annotations

import atexit
import logging
import os
import threading
from typing import Optional

from ...contracts import SendBudget
from .config_service import TraceConfigService
from .send_service import TraceSendService

logger = logging.getLogger(__name__)


class TraceDrainService:
    """Daemon thread that periodically sends the local queue."""

    _lock = threading.Lock()
    _started = False
    _stop = threading.Event()
    _thread: Optional[threading.Thread] = None

    @classmethod
    def start(cls) -> None:
        if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
            return
        with cls._lock:
            if cls._started:
                return
            cls._started = True
            cls._stop.clear()

            def _loop() -> None:
                while not cls._stop.wait(timeout=cls._interval_sec()):
                    try:
                        if not TraceConfigService.is_enabled():
                            continue
                        TraceSendService.send(budget=SendBudget.AUTO)
                    except Exception as exc:
                        logger.debug("background drain tick failed: %s", exc)

            cls._thread = threading.Thread(
                target=_loop,
                name="ntq-trace-drain",
                daemon=True,
            )
            cls._thread.start()
            atexit.register(cls._atexit_send)

    @classmethod
    def stop(cls) -> None:
        with cls._lock:
            cls._stop.set()
            cls._started = False
            cls._thread = None

    @classmethod
    def _interval_sec(cls) -> float:
        try:
            return max(5.0, float(TraceConfigService.load().bff_drain_interval_sec or 60))
        except Exception:
            return 60.0

    @classmethod
    def _atexit_send(cls) -> None:
        try:
            cls._stop.set()
            TraceSendService.send(budget=SendBudget.STANDARD)
        except Exception:
            pass
