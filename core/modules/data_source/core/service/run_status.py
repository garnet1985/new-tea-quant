"""一次 renew 的任务栏状态。

Drupal 只读运行目录里的 status.json。失败详情在 failures/ 下，不放进轮询文件。
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.modules.data_source.core.catalog.display_names import DEFAULT_DISPLAY_NAMES

KEEP_RUNS = 20
KEEP_DAYS = 14
_FAILURE_LINE_CAP = 200
_SUMMARY_LEN = 180


def ordered_source_keys(enabled: Dict[str, Dict[str, Any]]) -> List[str]:
    """按 depends_on 拓扑排序。保留依赖不计入。"""
    from collections import defaultdict, deque

    from core.modules.data_source.core.reserved_dependencies import RESERVED_DEPENDENCY_KEYS

    in_degree = {key: 0 for key in enabled}
    graph: Dict[str, List[str]] = defaultdict(list)
    for key, info in enabled.items():
        for dep_name in info.get("depends_on") or []:
            if dep_name in RESERVED_DEPENDENCY_KEYS or dep_name not in in_degree:
                continue
            graph[dep_name].append(key)
            in_degree[key] += 1
    queue = deque([key for key, degree in in_degree.items() if degree == 0])
    ordered: List[str] = []
    while queue:
        current = queue.popleft()
        ordered.append(current)
        for dependent in graph[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    if len(ordered) != len(enabled):
        missing = [key for key in enabled if key not in ordered]
        ordered.extend(missing)
    return ordered


def catalog_from_handlers(handlers: List[Any], *, force: bool = False) -> List[Dict[str, Any]]:
    """按即将执行的顺序生成任务栏。只含表名、中文名和更新模式。"""
    rows: List[Dict[str, Any]] = []
    for index, handler in enumerate(handlers, start=1):
        key = str(handler.get_key() or "")
        config = handler.context.get("config") if hasattr(handler, "context") else None
        table = ""
        if config is not None and hasattr(config, "get_table_name"):
            table = str(config.get_table_name() or "")
        mode = ""
        if hasattr(handler, "renew_mode_label"):
            mode = handler.renew_mode_label(force=force)
        rows.append(
            {
                "order": index,
                "source": key,
                "table": table,
                "name": DEFAULT_DISPLAY_NAMES.get(key, key),
                "mode": mode,
                "status": "pending",
                "plan_seconds": None,
                "execute_seconds": None,
                "started_at": None,
                "error": "",
                "error_log": "",
            }
        )
    return rows


def runs_directory() -> Optional[Path]:
    """状态目录的父目录。优先 NTQ_RUNS_DIR，否则用本次运行目录的上一级。"""
    raw = os.environ.get("NTQ_RUNS_DIR", "").strip()
    if raw:
        return Path(raw)
    run_dir = os.environ.get("NTQ_RUN_DIR", "").strip()
    if run_dir:
        return Path(run_dir).parent
    return _default_runs_directory()


def clear_finished_runs(parent: Optional[Path] = None) -> List[str]:
    """删掉已结束的运行目录。正在跑的那一次留下。"""
    root = parent or runs_directory()
    if root is None or not root.is_dir():
        return []
    return prune_runs(root, keep=0, days=0, current=None)


def prune_runs(
    parent: Path,
    *,
    keep: int = KEEP_RUNS,
    days: int = KEEP_DAYS,
    current: Optional[Path] = None,
) -> List[str]:
    """留下最近 keep 次、并且新于 days 天的运行目录。"""
    if not parent.is_dir():
        return []
    current_resolved = current.resolve() if current is not None else None
    runs = [path for path in parent.iterdir() if path.is_dir() and path.name.startswith("run-")]
    runs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    now = time.time()
    removed: List[str] = []
    for index, path in enumerate(runs):
        if current_resolved is not None and path.resolve() == current_resolved:
            continue
        if _run_is_alive(path):
            continue
        age_days = (now - path.stat().st_mtime) / 86400
        if index >= keep or age_days > days:
            shutil.rmtree(path, ignore_errors=True)
            removed.append(path.name)
    return removed


class RunStatus:
    """把任务栏写进运行目录。写失败不影响抓取。"""

    def __init__(self, run_dir: Optional[Path], tasks: List[Dict[str, Any]]):
        self.run_dir = run_dir
        self.tasks = tasks
        self._by_source = {row["source"]: row for row in tasks}

    @classmethod
    def open(cls, handlers: List[Any], *, force: bool = False) -> "RunStatus":
        tasks = catalog_from_handlers(handlers, force=force)
        run_dir = _prepare_run_dir()
        status = cls(run_dir, tasks)
        if run_dir is None:
            return status
        try:
            prune_runs(run_dir.parent, current=run_dir)
            status._write()
        except OSError:
            status.run_dir = None
        return status

    def mark_running(self, source: str) -> None:
        row = self._by_source.get(source)
        if row is None:
            return
        row["status"] = "running"
        row["started_at"] = int(time.time())
        row["error"] = ""
        row["error_log"] = ""
        self._write()

    def mark_done(self, handler: Any) -> None:
        source = str(handler.get_key() or "")
        row = self._by_source.get(source)
        if row is None:
            return
        timing = getattr(handler, "_last_run_timing", None) or {}
        context = getattr(handler, "context", {}) or {}
        row["status"] = "done"
        row["plan_seconds"] = _seconds(timing.get("plan"))
        row["execute_seconds"] = _seconds(timing.get("execute"))
        count = int(context.get("_bundle_error_count") or 0)
        lines = context.get("_bundle_errors") or []
        if count and isinstance(lines, list):
            row["error"] = _bundle_summary(count, lines)
            row["error_log"] = self._write_failure(source, lines)
        self._write()

    def mark_failed(self, handler: Any, error: BaseException) -> None:
        source = str(handler.get_key() or "")
        row = self._by_source.get(source)
        if row is None:
            return
        timing = getattr(handler, "_last_run_timing", None) or {}
        message = str(error).splitlines()[0][:_SUMMARY_LEN] if str(error) else error.__class__.__name__
        row["status"] = "failed"
        row["plan_seconds"] = _seconds(timing.get("plan"))
        row["execute_seconds"] = _seconds(timing.get("execute"))
        row["error"] = message
        row["error_log"] = self._write_failure(source, [message])
        self._write()

    def _write_failure(self, source: str, lines: List[str]) -> str:
        if self.run_dir is None:
            return ""
        safe = _safe_name(source)
        relative = f"failures/{safe}.log"
        path = self.run_dir / relative
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            return ""
        return relative

    def _write(self) -> None:
        if self.run_dir is None:
            return
        payload = {
            "pid": os.getpid(),
            "updated_at": int(time.time()),
            "tasks": self.tasks,
        }
        raw = json.dumps(payload, ensure_ascii=False, indent=2)
        target = self.run_dir / "status.json"
        temporary = self.run_dir / "status.json.tmp"
        temporary.write_text(raw, encoding="utf-8")
        temporary.replace(target)
        tasks_path = self.run_dir / "tasks.json"
        if not tasks_path.exists():
            tasks_path.write_text(
                json.dumps(self.tasks, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


def call_with_status(status: RunStatus, handler: Any, fn: Callable[[], Any]) -> Any:
    status.mark_running(str(handler.get_key() or ""))
    try:
        result = fn()
    except Exception as exc:
        status.mark_failed(handler, exc)
        raise
    status.mark_done(handler)
    return result


def _prepare_run_dir() -> Optional[Path]:
    raw = os.environ.get("NTQ_RUN_DIR", "").strip()
    if raw:
        path = Path(raw)
    else:
        parent = _default_runs_directory()
        if parent is None:
            return None
        path = parent / time.strftime("run-%Y%m%dT%H%M%S")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return path


def _default_runs_directory() -> Optional[Path]:
    try:
        from core.infra.project_context import ProjectContext

        return ProjectContext.path.get_userspace_root() / "system" / "run_status"
    except Exception:
        return None


def _run_is_alive(path: Path) -> bool:
    status_path = path / "status.json"
    if not status_path.is_file():
        return False
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list):
        return False
    if not any(isinstance(row, dict) and row.get("status") == "running" for row in tasks):
        return False
    return _pid_alive(int(payload.get("pid") or 0))


def _pid_alive(pid: int) -> bool:
    if pid < 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _seconds(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def _bundle_summary(count: int, lines: List[str]) -> str:
    head = ""
    if lines:
        head = str(lines[0]).split(":", 1)[-1].strip()[:_SUMMARY_LEN]
    if head:
        return f"失败 {count} 个任务：{head}"
    return f"失败 {count} 个任务"


def _safe_name(source: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in source)
    return cleaned or "task"
