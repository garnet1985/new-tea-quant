"""Strategy pipeline progress — weighted steps + disk persistence.

One submit = one pipeline. Steps are internal phases (load / dispatch /
execute / report), not enum/price/portfolio (those are pipeline names).

Callers bind a pipeline for the job thread, then drive lifecycle / ticks.
With no bind, classmethods are no-ops (CLI without progress file).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from .progress_recorder import ProgressRecorder

logger = logging.getLogger(__name__)

_SCHEMA = "strategy_pipeline_v1"
_BOUND: ContextVar[Optional["PipelineProgress"]] = ContextVar(
    "strategy_pipeline_progress", default=None
)

# Running with no disk update for this long → read path marks failed (UI escape).
_STALE_AFTER_SEC = 30 * 60

_STEPS: tuple[str, ...] = ("load", "dispatch", "execute", "report")

_STEP_WEIGHTS: Dict[str, Dict[str, float]] = {
    "enum": {"load": 0.05, "dispatch": 0.03, "execute": 0.9, "report": 0.02},
    "price": {"load": 0.1, "dispatch": 0.03, "execute": 0.85, "report": 0.02},
    "portfolio": {"load": 0.2, "dispatch": 0.1, "execute": 0.6, "report": 0.1},
}

_STEP_LABELS: Dict[str, str] = {
    "load": "加载数据",
    "dispatch": "调度任务",
    "execute": "回测中",
    "report": "生成报告",
}

_PIPELINE_LABELS: Dict[str, str] = {
    "enum": "枚举",
    "price": "价格回测",
    "portfolio": "资金模拟",
}

_TERMINAL = frozenset({"completed", "failed", "cancelled"})


class PipelineProgress:
    """Weighted pipeline progress service (compute + ProgressRecorder IO)."""

    def __init__(
        self,
        strategy_key: str,
        pipeline_id: str,
        *,
        doc: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.strategy_key = str(strategy_key or "").strip()
        self.pipeline_id = str(pipeline_id or "").strip()
        self._doc: Dict[str, Any] = dict(doc or {})
        self._exec_wave_total: Optional[int] = None
        self._exec_wave_done: int = 0

    # ── bind / lookup ─────────────────────────────────────────────

    @classmethod
    def current(cls) -> Optional["PipelineProgress"]:
        return _BOUND.get()

    @classmethod
    @contextmanager
    def bind(cls, strategy_key: str, pipeline_id: str) -> Iterator["PipelineProgress"]:
        inst = cls.load(strategy_key, pipeline_id)
        if inst is None:
            raise FileNotFoundError(
                f"pipeline progress not seeded: {strategy_key!r} / {pipeline_id!r}"
            )
        token: Token = _BOUND.set(inst)
        try:
            yield inst
        finally:
            _BOUND.reset(token)

    @classmethod
    def load(cls, strategy_key: str, pipeline_id: str) -> Optional["PipelineProgress"]:
        sn = str(strategy_key or "").strip()
        pid = str(pipeline_id or "").strip()
        if not sn or not pid:
            return None
        raw = ProgressRecorder.for_strategy_workbench_run(sn, pid).get_progress()
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            return None
        return cls(sn, pid, doc=raw)

    @staticmethod
    def pipeline_description(pipeline_name: str) -> str:
        key = str(pipeline_name or "").strip()
        return _PIPELINE_LABELS.get(key, key)

    @staticmethod
    def step_description(step_name: str) -> str:
        key = str(step_name or "").strip()
        return _STEP_LABELS.get(key, key)

    # ── seed / terminal writes (always keyed; no bind required) ───

    @classmethod
    def seed(
        cls,
        strategy_key: str,
        pipeline_id: str,
        *,
        pipeline_name: str,
        pipeline_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        sn = str(strategy_key or "").strip()
        pid = str(pipeline_id or "").strip()
        name = str(pipeline_name or "").strip()
        desc = (
            str(pipeline_description).strip()
            if pipeline_description is not None
            else cls.pipeline_description(name)
        )
        doc: Dict[str, Any] = {
            "schema": _SCHEMA,
            "pipeline_id": pid,
            "pipeline_name": name,
            "pipeline_description": desc,
            "strategy_key": sn,
            "status": "queued",
            "progress": 0.0,
            "step": None,
            "completed_steps": [],
            "error": None,
            "result": None,
        }
        cls(sn, pid, doc=doc)._save()
        return dict(doc)

    def mark_running(self) -> None:
        if self._status() in _TERMINAL:
            return
        self._doc["status"] = "running"
        self._doc["error"] = None
        self._save()

    def enter_step(self, step_name: str) -> None:
        if self._status() in _TERMINAL:
            return
        name = str(step_name or "").strip()
        if not name:
            return
        self._finalize_current_step()
        self._doc["status"] = "running"
        self._doc["step"] = {
            "name": name,
            "description": self.step_description(name),
            "progress": 0.0,
            "counters": None,
        }
        if name == "execute":
            self._exec_wave_total = None
            self._exec_wave_done = 0
        self._recompute_pipeline_progress()
        self._save()

    def complete_step(self, step_name: Optional[str] = None) -> None:
        if self._status() in _TERMINAL:
            return
        cur = self._doc.get("step")
        if not isinstance(cur, dict):
            return
        if step_name and str(cur.get("name") or "") != str(step_name).strip():
            return
        cur["progress"] = 100.0
        cur["counters"] = None
        self._doc["step"] = cur
        self._finalize_current_step()
        self._recompute_pipeline_progress()
        self._save()

    def tick_execute(self, done: int, total: int) -> None:
        if self._status() in _TERMINAL:
            return
        cur = self._doc.get("step")
        if not isinstance(cur, dict) or str(cur.get("name") or "") != "execute":
            self.enter_step("execute")
            cur = self._doc.get("step")
        if not isinstance(cur, dict):
            return

        d = max(0, int(done))
        t = max(0, int(total))
        # New BE wave (total changed or counter reset): keep step pct monotonic.
        if self._exec_wave_total is not None and (
            t != self._exec_wave_total or d < self._exec_wave_done
        ):
            try:
                prev = float(cur.get("progress") or 0.0)
            except (TypeError, ValueError):
                prev = 0.0
            # Close previous wave at least to its last ratio floor.
            cur["progress"] = max(prev, 0.0)
        self._exec_wave_total = t
        self._exec_wave_done = d

        ratio = 1.0 if t <= 0 and d > 0 else (float(d) / float(t) if t > 0 else 0.0)
        ratio = max(0.0, min(1.0, ratio))
        new_pct = round(ratio * 100.0, 2)
        try:
            old_pct = float(cur.get("progress") or 0.0)
        except (TypeError, ValueError):
            old_pct = 0.0
        cur["progress"] = max(old_pct, new_pct)
        cur["counters"] = {"done": d, "total": t}
        cur["description"] = self.step_description("execute")
        self._doc["step"] = cur
        self._doc["status"] = "running"
        self._recompute_pipeline_progress()
        self._save()

    def complete(self, *, result: Optional[Dict[str, Any]] = None) -> None:
        if self._status() == "cancelled":
            return
        self._finalize_current_step()
        # Ensure remaining planned steps are marked completed for interrupt clarity.
        done_names = {
            str(x.get("name") or "")
            for x in (self._doc.get("completed_steps") or [])
            if isinstance(x, dict)
        }
        for name in _STEPS:
            if name not in done_names:
                self._doc.setdefault("completed_steps", []).append(
                    {"name": name, "description": self.step_description(name)}
                )
                done_names.add(name)
        self._doc["step"] = None
        self._doc["status"] = "completed"
        self._doc["progress"] = 100.0
        self._doc["error"] = None
        if result is not None:
            self._doc["result"] = dict(result)
        self._save()

    def fail(self, message: str) -> None:
        if self._status() in ("completed", "cancelled"):
            return
        msg = str(message or "").strip() or "执行失败"
        self._doc["status"] = "failed"
        self._doc["error"] = msg
        self._save()

    def cancel(self, message: str = "已取消") -> None:
        if self._status() in ("completed", "failed"):
            return
        self._doc["status"] = "cancelled"
        self._doc["error"] = str(message or "").strip() or "已取消"
        self._save()

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._doc)

    # ── classmethod facades (bound thread) ────────────────────────

    @classmethod
    def mark_running_bound(cls) -> None:
        cur = cls.current()
        if cur is not None:
            cur.mark_running()

    @classmethod
    def enter_step_bound(cls, step_name: str) -> None:
        cur = cls.current()
        if cur is not None:
            cur.enter_step(step_name)

    @classmethod
    def complete_step_bound(cls, step_name: Optional[str] = None) -> None:
        cur = cls.current()
        if cur is not None:
            cur.complete_step(step_name)

    @classmethod
    def tick_execute_bound(cls, done: int, total: int) -> None:
        cur = cls.current()
        if cur is not None:
            cur.tick_execute(done, total)

    @classmethod
    def tick_from_run_progress(cls, progress: Any) -> None:
        cur = cls.current()
        if cur is None or progress is None:
            return
        try:
            done = int(getattr(progress, "finished", 0) or 0)
            total = int(getattr(progress, "total", 0) or 0)
        except (TypeError, ValueError):
            return
        cur.tick_execute(done, total)

    @classmethod
    def drives_pipeline(cls, pipeline_name: str) -> bool:
        """True when bound progress belongs to this pipeline name."""
        cur = cls.current()
        if cur is None:
            return False
        return str(cur._doc.get("pipeline_name") or "") == str(pipeline_name or "").strip()

    @classmethod
    def get(
        cls,
        strategy_key: str,
        pipeline_id: str,
        *,
        apply_stale: bool = True,
    ) -> Optional[Dict[str, Any]]:
        inst = cls.load(strategy_key, pipeline_id)
        if inst is None:
            return None
        if apply_stale:
            inst._maybe_mark_stale()
        return inst.to_dict()

    # ── internals ─────────────────────────────────────────────────

    def _status(self) -> str:
        return str(self._doc.get("status") or "").strip().lower()

    def _weights(self) -> Dict[str, float]:
        name = str(self._doc.get("pipeline_name") or "").strip()
        return dict(_STEP_WEIGHTS.get(name, _STEP_WEIGHTS["price"]))

    def _finalize_current_step(self) -> None:
        cur = self._doc.get("step")
        if not isinstance(cur, dict):
            return
        name = str(cur.get("name") or "").strip()
        if not name:
            self._doc["step"] = None
            return
        completed = list(self._doc.get("completed_steps") or [])
        # Avoid duplicate tail when re-entering after partial finalize.
        if not (
            completed
            and isinstance(completed[-1], dict)
            and str(completed[-1].get("name") or "") == name
        ):
            completed.append(
                {
                    "name": name,
                    "description": str(
                        cur.get("description") or self.step_description(name)
                    ),
                }
            )
        self._doc["completed_steps"] = completed
        self._doc["step"] = None

    def _recompute_pipeline_progress(self) -> None:
        weights = self._weights()
        done_names = {
            str(x.get("name") or "")
            for x in (self._doc.get("completed_steps") or [])
            if isinstance(x, dict)
        }
        acc = 0.0
        for name in _STEPS:
            if name in done_names:
                acc += float(weights.get(name) or 0.0)
        cur = self._doc.get("step")
        if isinstance(cur, dict):
            name = str(cur.get("name") or "").strip()
            if name and name not in done_names:
                try:
                    step_pct = float(cur.get("progress") or 0.0)
                except (TypeError, ValueError):
                    step_pct = 0.0
                acc += float(weights.get(name) or 0.0) * max(
                    0.0, min(1.0, step_pct / 100.0)
                )
        self._doc["progress"] = round(max(0.0, min(100.0, acc * 100.0)), 2)

    def _maybe_mark_stale(self) -> None:
        if self._status() != "running":
            return
        raw_ts = self._doc.get("updated_at")
        if not raw_ts:
            return
        try:
            ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            return
        if age < _STALE_AFTER_SEC:
            return
        logger.warning(
            "pipeline progress stale strategy=%s id=%s age_sec=%.0f",
            self.strategy_key,
            self.pipeline_id,
            age,
        )
        self.fail("进度超时未更新，任务可能已中断")

    def _save(self) -> None:
        self._recompute_pipeline_progress()
        ProgressRecorder.for_strategy_workbench_run(
            self.strategy_key, self.pipeline_id
        ).record(self._doc)


__all__ = ["PipelineProgress"]
