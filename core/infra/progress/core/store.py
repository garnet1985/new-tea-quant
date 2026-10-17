"""当前任务进度的读写。对外只经过 Progress。"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_MEMORY: Optional[Dict[str, Any]] = None
_LAST_WRITE = 0.0
_WRITE_INTERVAL = 1.0


def _empty() -> Dict[str, Any]:
    return {
        "job": "",
        "source": "",
        "step": 0,
        "step_total": 0,
        "sub": 0,
        "sub_total": 0,
        "updated_at": 0,
    }


def _count(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def progress_path() -> Optional[Path]:
    """进度文件路径。测试可设 NTQ_PROGRESS_FILE。"""
    raw = os.environ.get("NTQ_PROGRESS_FILE", "").strip()
    if raw:
        return Path(raw)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / "ntq-progress-test.json"
    try:
        from core.infra.project_context import ProjectContext

        return ProjectContext.path.get_userspace_tmp_directory() / "progress.json"
    except Exception:
        return None


def _fraction(step: int, step_total: int, sub: int = 0, sub_total: int = 0) -> float:
    """0 到 1。总步骤为 0 时是 0。"""
    total = _count(step_total)
    if total <= 0:
        return 0.0
    done = min(_count(step), total)
    inner_total = _count(sub_total)
    inner = 0.0
    if inner_total > 0:
        inner = min(_count(sub), inner_total) / inner_total
    return max(0.0, min(1.0, (done + inner) / total))


class Progress:
    """更新和读取当前任务进度。写失败不影响任务本身。"""

    @staticmethod
    def open(source: str, step_total: int, *, job: str = "") -> None:
        """开始一次任务。已完成步骤为 0。"""
        state = _empty()
        state["job"] = str(job or "")
        state["source"] = str(source or "")
        state["step_total"] = _count(step_total)
        state["updated_at"] = int(time.time())
        _store(state, force=True)

    @staticmethod
    def step(
        done: int,
        total: Optional[int] = None,
        *,
        source: Optional[str] = None,
        job: Optional[str] = None,
    ) -> None:
        """已经完成的步骤。进入这一步时，子步骤清零。"""
        state = _current()
        if total is not None:
            state["step_total"] = _count(total)
        finished = _count(done)
        cap = _count(state.get("step_total"))
        if cap and finished > cap:
            finished = cap
        state["step"] = finished
        state["sub"] = 0
        state["sub_total"] = 0
        if source is not None:
            state["source"] = str(source or "")
        if job is not None:
            state["job"] = str(job or "")
        state["updated_at"] = int(time.time())
        _store(state, force=True)

    @staticmethod
    def sub(done: int, total: int, *, source: Optional[str] = None) -> None:
        """当前步骤里的子步骤。"""
        state = _current()
        state["sub"] = _count(done)
        state["sub_total"] = _count(total)
        if source:
            state["source"] = str(source)
        state["updated_at"] = int(time.time())
        _store(state, force=False)

    @staticmethod
    def close() -> None:
        """这次任务结束。步骤收到总数，子步骤清零。"""
        state = _current()
        total = _count(state.get("step_total"))
        if total:
            state["step"] = total
        state["sub"] = 0
        state["sub_total"] = 0
        state["updated_at"] = int(time.time())
        _store(state, force=True)

    @staticmethod
    def read() -> Dict[str, Any]:
        """外部读取。没有进度文件时，各数字为 0。"""
        with _LOCK:
            memory = dict(_MEMORY) if _MEMORY else None
        disk = _read_file()
        if memory is None:
            return disk
        if _count(memory.get("updated_at")) >= _count(disk.get("updated_at")):
            return memory
        return disk

    @staticmethod
    def fraction(step: int, step_total: int, sub: int = 0, sub_total: int = 0) -> float:
        """显示层可用的同一条比例。0 到 1。"""
        return _fraction(step, step_total, sub, sub_total)


def _current() -> Dict[str, Any]:
    with _LOCK:
        if _MEMORY is not None:
            return dict(_MEMORY)
    disk = _read_file()
    if disk.get("updated_at"):
        return disk
    return _empty()


def _read_file() -> Dict[str, Any]:
    path = progress_path()
    if path is None or not path.is_file():
        return _empty()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
    if not isinstance(raw, dict):
        return _empty()
    state = _empty()
    state["job"] = str(raw.get("job") or "")
    state["source"] = str(raw.get("source") or "")
    state["step"] = _count(raw.get("step"))
    state["step_total"] = _count(raw.get("step_total"))
    state["sub"] = _count(raw.get("sub"))
    state["sub_total"] = _count(raw.get("sub_total"))
    state["updated_at"] = _count(raw.get("updated_at"))
    return state


def _store(state: Dict[str, Any], *, force: bool) -> None:
    global _MEMORY, _LAST_WRITE
    now = time.time()
    with _LOCK:
        _MEMORY = dict(state)
        if not force and now - _LAST_WRITE < _WRITE_INTERVAL:
            return
        _LAST_WRITE = now
    _write_file(state)


def _write_file(state: Dict[str, Any]) -> None:
    path = progress_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(state, ensure_ascii=False, indent=2)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(raw, encoding="utf-8")
        temporary.replace(path)
    except OSError:
        return
