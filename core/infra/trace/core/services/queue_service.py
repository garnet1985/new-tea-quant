"""Local file queue for TraceEvent (one JSON file per event)."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from ...contracts import TraceEvent

logger = logging.getLogger(__name__)

_STALE_INFLIGHT_SEC = 300


class TraceQueueService:
    """Disk outbox under userspace/.ntq/trace/{queue,inflight}."""

    @staticmethod
    def depth() -> int:
        _, queue, _ = TraceQueueService._dirs()
        if queue is None:
            return 0
        try:
            return sum(1 for p in queue.iterdir() if p.is_file() and p.suffix == ".json")
        except Exception:
            return 0

    @staticmethod
    def enqueue(event: TraceEvent, *, queue_max: int = 100) -> bool:
        _, queue, _ = TraceQueueService._dirs()
        if queue is None:
            return False
        try:
            event_id = str(event.event_id or uuid.uuid4())
            name = f"{int(time.time() * 1000):013d}_{event_id}.json"
            path = queue / name
            tmp = queue / f".{name}.tmp"
            tmp.write_text(
                json.dumps(event.to_dict(), ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(tmp, path)
            TraceQueueService._enforce_max(queue, queue_max)
            return True
        except Exception as exc:
            logger.debug("trace enqueue failed: %s", exc)
            try:
                if "tmp" in locals() and tmp.exists():  # type: ignore[name-defined]
                    tmp.unlink(missing_ok=True)  # type: ignore[name-defined]
            except Exception:
                pass
            return False

    @staticmethod
    def claim_next() -> Optional[Tuple[Path, TraceEvent]]:
        _, queue, inflight = TraceQueueService._dirs()
        if queue is None or inflight is None:
            return None
        TraceQueueService.reclaim_stale_inflight()
        try:
            files = sorted(
                (p for p in queue.iterdir() if p.is_file() and p.suffix == ".json"),
                key=lambda p: p.name,
            )
            for src in files:
                dest = inflight / f"{src.name}.{os.getpid()}"
                try:
                    os.rename(src, dest)
                except FileNotFoundError:
                    continue
                except OSError:
                    continue
                event = TraceQueueService._read_event(dest)
                if event is None:
                    try:
                        dest.unlink(missing_ok=True)
                    except Exception:
                        pass
                    continue
                return dest, event
        except Exception as exc:
            logger.debug("claim_next failed: %s", exc)
        return None

    @staticmethod
    def complete(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            logger.debug("complete unlink failed: %s", exc)

    @staticmethod
    def requeue(path: Path, event: TraceEvent, *, max_attempts: int = 10) -> None:
        attempts = int(event.attempts or 0) + 1
        bumped = TraceEvent(
            schema_version=event.schema_version,
            event_id=event.event_id,
            installation_id=event.installation_id,
            event=event.event,
            occurred_at=event.occurred_at,
            meta=dict(event.meta or {}),
            body=dict(event.body or {}),
            attempts=attempts,
        )
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        if attempts >= max_attempts:
            return
        TraceQueueService.enqueue(bumped, queue_max=10_000)

    @staticmethod
    def reclaim_stale_inflight(*, max_age_sec: int = _STALE_INFLIGHT_SEC) -> None:
        _, queue, inflight = TraceQueueService._dirs()
        if queue is None or inflight is None:
            return
        now = time.time()
        try:
            for path in list(inflight.iterdir()):
                if not path.is_file():
                    continue
                try:
                    age = now - path.stat().st_mtime
                    if age < max_age_sec:
                        continue
                    name = path.name
                    if name.count(".") >= 2:
                        base, _pid = name.rsplit(".", 1)
                        if base.endswith(".json"):
                            name = base
                    dest = queue / name
                    if dest.exists():
                        path.unlink(missing_ok=True)
                    else:
                        os.replace(path, dest)
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("reclaim inflight failed: %s", exc)

    @staticmethod
    def purge() -> int:
        """Delete all pending and in-flight events (used when consent is revoked)."""
        _, queue, inflight = TraceQueueService._dirs()
        removed = 0
        for folder in (queue, inflight):
            if folder is None:
                continue
            try:
                for path in list(folder.iterdir()):
                    if not path.is_file():
                        continue
                    try:
                        path.unlink(missing_ok=True)
                        removed += 1
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug("queue purge failed: %s", exc)
        return removed

    @staticmethod
    def list_files() -> List[Path]:
        _, queue, _ = TraceQueueService._dirs()
        if queue is None:
            return []
        try:
            return sorted(
                (p for p in queue.iterdir() if p.is_file() and p.suffix == ".json"),
                key=lambda p: p.name,
            )
        except Exception:
            return []

    @staticmethod
    def _dirs() -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
        try:
            from core.infra.project_context import ProjectContext

            root = ProjectContext.path.get_userspace_ntq_directory() / "trace"
            queue = root / "queue"
            inflight = root / "inflight"
            queue.mkdir(parents=True, exist_ok=True)
            inflight.mkdir(parents=True, exist_ok=True)
            return root, queue, inflight
        except Exception as exc:
            logger.debug("trace dirs unavailable: %s", exc)
            return None, None, None

    @staticmethod
    def _enforce_max(queue: Path, queue_max: int) -> None:
        if queue_max <= 0:
            return
        try:
            files = sorted(
                (p for p in queue.iterdir() if p.is_file() and p.suffix == ".json"),
                key=lambda p: p.name,
            )
            overflow = len(files) - queue_max
            for path in files[: max(0, overflow)]:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("queue max enforce failed: %s", exc)

    @staticmethod
    def _read_event(path: Path) -> Optional[TraceEvent]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return TraceEvent.from_dict(raw if isinstance(raw, dict) else None)
