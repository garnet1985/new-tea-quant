"""安装和导入的进度文件。断点续传仍写 .import_progress.json。"""

from __future__ import annotations

from typing import Iterable, Optional

from core.infra.progress import Progress

INSTALL_ID = "install"
IMPORT_ID = "import"
_ACTIVE = frozenset({"running", "paused"})


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
    Progress.start(IMPORT_ID, job="import", label="导入数据", steps=steps)
    for name in ordered:
        if name in done:
            Progress.finish(_child_id(IMPORT_ID, name))


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
    completed = _completed_count(snap)
    total = int(snap.get("total") or 0)
    return {
        "running": running,
        "totalTables": total,
        "completedCount": completed,
        "currentTable": str((leaf or {}).get("source") or "") if running else "",
        "ratio": float(snap.get("ratio") or 0),
    }


def _empty_import_progress() -> dict:
    return {
        "running": False,
        "totalTables": 0,
        "completedCount": 0,
        "currentTable": "",
        "ratio": 0,
    }


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
