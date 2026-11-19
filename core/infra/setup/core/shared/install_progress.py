"""安装和导入的进度文件。断点续传仍写 .import_progress.json。"""

from __future__ import annotations

import time
from typing import Iterable, Optional

from core.infra.progress import Progress

INSTALL_ID = "install"
IMPORT_ID = "import"
DOWNLOAD_STEP = "download"
PREPARE_STEP = "prepare"
_ACTIVE = frozenset({"running", "paused"})
_STATUS_STEPS = frozenset({DOWNLOAD_STEP, PREPARE_STEP})
_DOWNLOAD_TICK_MIN_INTERVAL_SEC = 0.25
_last_download_tick_at = 0.0
_last_download_parts_done = -1


def open_install(step_ids: Iterable[str], *, done_ids: Iterable[str] = ()) -> None:
    """每个安装步骤一层。已经成功的步骤直接标完成。"""
    done = {str(step_id) for step_id in done_ids}
    steps = []
    seen = set()
    ordered = []
    for step_id in step_ids:
        name = str(step_id or "")
        node_id = _child_id(INSTALL_ID, name)
        if not name or node_id in seen:
            continue
        seen.add(node_id)
        ordered.append(name)
        steps.append({"id": node_id, "label": name})
    if not steps:
        return
    Progress.start(INSTALL_ID, job="install", label="安装", steps=steps)
    for name in ordered:
        if name in done:
            Progress.finish(_child_id(INSTALL_ID, name))


def begin_install_step(step_id: str) -> None:
    Progress.tick(_child_id(INSTALL_ID, step_id), 0, 1, source=step_id, log=False)


def finish_install_step(step_id: str) -> None:
    Progress.finish(_child_id(INSTALL_ID, step_id))


def pause_install_step(step_id: str) -> None:
    Progress.pause(_child_id(INSTALL_ID, step_id))


def close_install() -> None:
    _quiet(lambda: Progress.finish(INSTALL_ID))


def fail_install(step_id: str, detail: str = "") -> None:
    message = _first_line(detail)
    if step_id:
        _quiet(lambda: Progress.fail(_child_id(INSTALL_ID, step_id), detail=message))
    _quiet(lambda: Progress.fail(INSTALL_ID, detail=message))


def clear_import_progress() -> None:
    """清掉上次导入的进度信息。"""
    _quiet(lambda: Progress.clear(IMPORT_ID))


def begin_import_prepare(*, detail: str = "准备导入…") -> None:
    """解压 / 建连之前的占位，避免步骤已开始却长时间无文案。"""
    from core.infra.progress.core import store as progress_store

    node = _child_id(IMPORT_ID, PREPARE_STEP)
    Progress.start(
        IMPORT_ID,
        job="import",
        label="导入数据",
        steps=[{"id": node, "label": PREPARE_STEP}],
    )
    Progress.tick(
        node,
        0,
        1,
        source=PREPARE_STEP,
        detail=str(detail or "准备导入…"),
        log=False,
    )
    progress_store.drain()


def begin_import_download(*, total_bytes: Optional[int] = None) -> None:
    """官网拉演示包：进度树先挂 download 一步，供 UI 显示下载进度。"""
    global _last_download_tick_at, _last_download_parts_done
    from core.infra.progress.core import store as progress_store

    _last_download_tick_at = 0.0
    _last_download_parts_done = -1
    node = _child_id(IMPORT_ID, DOWNLOAD_STEP)
    total = max(0, int(total_bytes or 0))
    Progress.start(
        IMPORT_ID,
        job="import",
        label="导入数据",
        steps=[{"id": node, "label": DOWNLOAD_STEP}],
    )
    Progress.tick(
        node,
        0,
        total,
        source=DOWNLOAD_STEP,
        detail=_download_detail(0, total),
        log=False,
    )
    # 子进程立刻落盘，BFF 轮询才能马上读到 downloading。
    progress_store.drain()


def tick_import_download(
    read_bytes: int,
    total_bytes: Optional[int] = None,
    *,
    parts_done: int = 0,
    parts_total: int = 0,
) -> None:
    """下载过程中更新字节 / 分卷进度（节流写入，避免每个 chunk 打满磁盘）。"""
    global _last_download_tick_at, _last_download_parts_done

    read = max(0, int(read_bytes or 0))
    total = max(0, int(total_bytes or 0))
    done_parts = max(0, int(parts_done or 0))
    total_parts = max(0, int(parts_total or 0))
    now = time.monotonic()
    finished = (total > 0 and read >= total) or (
        total_parts > 0 and done_parts >= total_parts
    )
    parts_changed = total_parts > 0 and done_parts != _last_download_parts_done
    if (
        not finished
        and not parts_changed
        and _last_download_tick_at > 0
        and (now - _last_download_tick_at) < _DOWNLOAD_TICK_MIN_INTERVAL_SEC
    ):
        return
    _last_download_tick_at = now
    _last_download_parts_done = done_parts
    Progress.tick(
        _child_id(IMPORT_ID, DOWNLOAD_STEP),
        read,
        total,
        source=DOWNLOAD_STEP,
        detail=_download_detail(
            read,
            total,
            parts_done=done_parts,
            parts_total=total_parts,
        ),
        log=False,
    )


def finish_import_download() -> None:
    from core.infra.progress.core import store as progress_store

    _quiet(lambda: Progress.finish(_child_id(IMPORT_ID, DOWNLOAD_STEP)))
    progress_store.drain()


def open_import(table_names: Iterable[str], *, done_names: Iterable[str] = ()) -> None:
    """每张表一层。这次已经导入过的表直接标完成。"""
    done = {str(name) for name in done_names}
    steps = []
    seen = set()
    ordered = []
    for table_name in table_names:
        name = str(table_name or "")
        node_id = _child_id(IMPORT_ID, name)
        if not name or node_id in seen:
            continue
        seen.add(node_id)
        ordered.append(name)
        steps.append({"id": node_id, "label": name})
    if not steps:
        return
    from core.infra.progress.core import store as progress_store

    Progress.start(IMPORT_ID, job="import", label="导入数据", steps=steps)
    for name in ordered:
        if name in done:
            Progress.finish(_child_id(IMPORT_ID, name))
    progress_store.drain()


def begin_import_table(table_name: str) -> None:
    Progress.tick(_child_id(IMPORT_ID, table_name), 0, 1, source=table_name, log=False)


def finish_import_table(table_name: str) -> None:
    Progress.finish(_child_id(IMPORT_ID, table_name))


def fail_import_table(table_name: str, detail: str = "") -> None:
    Progress.fail(_child_id(IMPORT_ID, table_name), detail=_first_line(detail))


def cancel_import_table(table_name: str, detail: str = "") -> None:
    Progress.cancel(_child_id(IMPORT_ID, table_name), detail=_first_line(detail))


def close_import() -> None:
    _quiet(lambda: Progress.finish(IMPORT_ID))


def fail_import(detail: str = "") -> None:
    _quiet(lambda: Progress.fail(IMPORT_ID, detail=_first_line(detail)))


def cancel_import(detail: str = "") -> None:
    _quiet(lambda: Progress.cancel(IMPORT_ID, detail=_first_line(detail)))


def read_import_progress() -> dict:
    """给安装页的字段。完成数只算已经导入成功的表。"""
    snap = Progress.latest("import")
    if not isinstance(snap, dict):
        return _empty_import_progress()
    status = str(snap.get("status") or "")
    running = status in _ACTIVE
    current = _deepest(snap, _ACTIVE) if running else None
    leaf = current if current and current.get("id") != snap.get("id") else None
    source = str((leaf or {}).get("source") or "") if running else ""
    # 仅含 download/prepare 的树（含刚下载完、子步已 completed）都算准备/下载，勿当成导表 1/1。
    only_status_tree = _only_status_steps(snap)
    if running and (source in _STATUS_STEPS or (only_status_tree and not source)):
        detail = str((leaf or {}).get("detail") or "").strip()
        leaf_done = int((leaf or {}).get("done") or 0)
        leaf_total = int((leaf or {}).get("total") or 0)
        leaf_ratio = float((leaf or {}).get("ratio") or 0)
        if source == DOWNLOAD_STEP:
            return {
                "running": True,
                "phase": "downloading",
                "statusText": detail or _download_detail(leaf_done, leaf_total),
                "totalTables": 0,
                "completedCount": 0,
                "currentTable": "",
                "ratio": leaf_ratio if leaf_total > 0 else 0,
                "downloadedBytes": leaf_done,
                "totalBytes": leaf_total,
            }
        return {
            "running": True,
            "phase": "preparing",
            "statusText": detail or "准备导入…",
            "totalTables": 0,
            "completedCount": 0,
            "currentTable": "",
            "ratio": 0,
            "downloadedBytes": 0,
            "totalBytes": 0,
        }
    completed = _completed_count(snap)
    total = int(snap.get("total") or 0)
    return {
        "running": running,
        "phase": "importing" if running else "",
        "statusText": "",
        "totalTables": total,
        "completedCount": completed,
        "currentTable": source if running else "",
        "ratio": float(snap.get("ratio") or 0),
        "downloadedBytes": 0,
        "totalBytes": 0,
    }


def _empty_import_progress() -> dict:
    return {
        "running": False,
        "phase": "",
        "statusText": "",
        "totalTables": 0,
        "completedCount": 0,
        "currentTable": "",
        "ratio": 0,
        "downloadedBytes": 0,
        "totalBytes": 0,
    }


def _only_status_steps(snap: dict) -> bool:
    steps = [child for child in (snap.get("steps") or []) if isinstance(child, dict)]
    if not steps:
        return False
    labels = {str(child.get("label") or "").strip() for child in steps}
    return bool(labels) and labels <= _STATUS_STEPS


def _download_detail(
    read_bytes: int,
    total_bytes: int,
    *,
    parts_done: int = 0,
    parts_total: int = 0,
) -> str:
    read = max(0, int(read_bytes or 0))
    total = max(0, int(total_bytes or 0))
    done_parts = max(0, int(parts_done or 0))
    total_parts = max(0, int(parts_total or 0))
    if total_parts > 0:
        base = f"数据下载中… {done_parts}/{total_parts} 包"
        if total > 0:
            pct = min(100, int(read * 100 / total))
            return f"{base} · {_format_mb(read)}/{_format_mb(total)} MB（{pct}%）"
        if read > 0:
            return f"{base} · 已下载 {_format_mb(read)} MB"
        return base
    if total > 0:
        pct = min(100, int(read * 100 / total))
        return (
            f"数据下载中… {_format_mb(read)}/{_format_mb(total)} MB（{pct}%）"
        )
    if read > 0:
        return f"数据下载中… 已下载 {_format_mb(read)} MB"
    return "数据下载中…"


def _format_mb(size_bytes: int) -> str:
    return f"{max(0, int(size_bytes or 0)) / (1024 * 1024):.1f}"


def _completed_count(node: dict) -> int:
    steps = [child for child in (node.get("steps") or []) if isinstance(child, dict)]
    if not steps:
        return 1 if str(node.get("status") or "") == "completed" else 0
    return sum(_completed_count(child) for child in steps)


def _deepest(node: dict, statuses: frozenset) -> Optional[dict]:
    found = node if str(node.get("status") or "") in statuses else None
    for child in node.get("steps") or []:
        if not isinstance(child, dict):
            continue
        deeper = _deepest(child, statuses)
        if deeper is not None:
            found = deeper
    return found


def _child_id(root: str, name: str) -> str:
    safe = str(name or "").replace("/", "-").replace("\\", "-").replace("\x00", "")
    return f"{root}:{safe}"


def _first_line(detail: str) -> str:
    text = str(detail or "")
    return text.splitlines()[0] if text else ""


def _quiet(action) -> None:
    try:
        action()
    except FileNotFoundError:
        return
