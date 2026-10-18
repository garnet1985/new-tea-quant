"""进度文件的读写。对外只经过 Progress。"""
from __future__ import annotations

import atexit
import copy
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

_LOCK = threading.Lock()
_BY_ROOT: Dict[str, Dict[str, Any]] = {}
_ROOT_OF: Dict[str, str] = {}
_DIRTY: Dict[str, Dict[str, Any]] = {}
_WRITER_ALIVE = False

_KEEP_FILES = 20
_KEEP_DAYS = 14
_FLUSH_DELAY = 0.2
_TERMINAL = frozenset({"completed", "failed", "cancelled"})
_PASSED = frozenset({"completed", "failed"})


def reset() -> None:
    """清空内存索引。测试使用。"""
    global _WRITER_ALIVE
    with _LOCK:
        _BY_ROOT.clear()
        _ROOT_OF.clear()
        _DIRTY.clear()
        _WRITER_ALIVE = False


def drain() -> None:
    """把尚未落盘的快照写出去。测试和进程退出时使用。"""
    with _LOCK:
        batch = dict(_DIRTY)
        _DIRTY.clear()
    for root_id, snapshot in batch.items():
        _write_file(root_id, snapshot)


def start(
    node_id: str,
    *,
    job: str = "",
    label: str = "",
    weight: float = 1,
    steps: Optional[Sequence[Mapping[str, Any]]] = None,
) -> None:
    """创建或覆盖一棵进度树，并写到以根 id 命名的文件。"""
    root = _build_node(
        {
            "id": node_id,
            "job": job,
            "label": label,
            "weight": weight,
            "steps": list(steps or []),
        },
        job=str(job or ""),
        status="running",
    )
    incoming = _collect_ids(root)
    with _LOCK:
        _refresh_index()
        for item_id in incoming:
            owner = _ROOT_OF.get(item_id)
            if owner is not None and owner != root["id"]:
                raise ValueError(f"进度 id 已存在: {item_id}")
        _drop_index(root["id"])
        _index_tree(root)
        _prune(job=str(root["job"]), keep_root=root["id"])
        _publish(root["id"])


def tick(
    node_id: str,
    done: int,
    total: int,
    *,
    source: Optional[str] = None,
    label: Optional[str] = None,
    detail: Optional[str] = None,
    log: bool = True,
) -> None:
    """更新一个叶子节点的计数。调用一次，状态改一次；log 为真时打一行日志。"""
    done_count = _count(done, "done")
    total_count = _count(total, "total")
    if total_count and done_count > total_count:
        done_count = total_count

    def apply(node: Dict[str, Any]) -> None:
        if node["steps"]:
            raise ValueError(f"进度 {node['id']} 有子节点，要更新子节点")
        node["status"] = "running"
        if not node["started_at"]:
            node["started_at"] = int(time.time())
        node["done"] = done_count
        node["total"] = total_count
        if source is not None:
            node["source"] = str(source)
        if label is not None:
            node["label"] = str(label)
        if detail is not None:
            node["detail"] = str(detail)

    snapshot = _mutate(node_id, apply)
    if log:
        _print_tick(snapshot, detail)


def finish(node_id: str) -> None:
    """把这个节点标成完成，ratio 为 1。不改其它节点的状态。"""

    def apply(node: Dict[str, Any]) -> None:
        node["status"] = "completed"

    _mutate(node_id, apply)


def fail(node_id: str, detail: str = "") -> None:
    """把这个节点标成失败。父节点继续。"""

    def apply(node: Dict[str, Any]) -> None:
        node["status"] = "failed"
        if detail:
            node["detail"] = str(detail)

    _mutate(node_id, apply)


def cancel(node_id: str, detail: str = "") -> None:
    """把这个节点标成取消。ratio 停在原地。"""

    def apply(node: Dict[str, Any]) -> None:
        node["status"] = "cancelled"
        if detail:
            node["detail"] = str(detail)

    _mutate(node_id, apply)


def pause(node_id: str) -> None:
    """暂停这个节点。计数不动。"""

    def apply(node: Dict[str, Any]) -> None:
        node["status"] = "paused"

    _mutate(node_id, apply)


def resume(node_id: str) -> None:
    """把暂停的节点恢复为运行。"""

    def apply(node: Dict[str, Any]) -> None:
        node["status"] = "running"

    _mutate(node_id, apply)


def clear(node_id: str) -> None:
    """删除包含该节点的根文件。"""
    with _LOCK:
        located = _locate(node_id)
        if located is None:
            raise FileNotFoundError(f"进度不存在: {node_id}")
        root = located[2]
        root_id = str(root["id"])
        _drop_index(root_id)
        _DIRTY.pop(root_id, None)
        path = _directory() / f"{root_id}.json"
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def read(node_id: str) -> Optional[Dict[str, Any]]:
    """读取包含该节点的整份根文件。没有则返回 None。"""
    with _LOCK:
        located = _locate(node_id)
        if located is None:
            return None
        return copy.deepcopy(located[2])


def latest(job: str) -> Optional[Dict[str, Any]]:
    """同一个 job 里 updated_at 最新的根文件。没有则返回 None。"""
    with _LOCK:
        _refresh_index()
        found: Optional[Dict[str, Any]] = None
        for root in _BY_ROOT.values():
            if str(root.get("job") or "") != str(job or ""):
                continue
            if found is None or _count_loose(root.get("updated_at")) >= _count_loose(found.get("updated_at")):
                found = root
        if found is None:
            return None
        return copy.deepcopy(found)


def _mutate(node_id: str, apply: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
    with _LOCK:
        located = _locate(node_id)
        if located is None:
            raise FileNotFoundError(f"进度不存在: {node_id}")
        node, ancestors, root = located
        apply(node)
        now = int(time.time())
        node["updated_at"] = now
        for parent in ancestors:
            parent["updated_at"] = now
        _recompute(root)
        _publish(str(root["id"]))
        return copy.deepcopy(node)


def _build_node(raw: Mapping[str, Any], *, job: str, status: str) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("进度节点必须是字典")
    node_id = str(raw.get("id") or "").strip()
    _check_node_id(node_id)
    node_job = str(raw.get("job") or job or "")
    label = str(raw.get("label") or "")
    node = _blank(node_id, job=node_job, label=label, weight=_weight(raw.get("weight", 1)), status=status)
    children = raw.get("steps") or []
    if not isinstance(children, Sequence) or isinstance(children, (str, bytes)):
        raise ValueError(f"进度 {node_id} 的 steps 必须是列表")
    node["steps"] = [
        _build_node(child, job=node_job, status="pending")
        for child in children
    ]
    seen: List[str] = []
    for item_id in _collect_ids(node):
        if item_id in seen:
            raise ValueError(f"进度 id 重复: {item_id}")
        seen.append(item_id)
    _recompute(node)
    return node


def _blank(node_id: str, *, job: str, label: str, weight: float, status: str) -> Dict[str, Any]:
    now = int(time.time()) if status == "running" else 0
    return {
        "id": node_id,
        "job": job,
        "status": status,
        "source": "",
        "label": label,
        "detail": "",
        "weight": weight,
        "done": 0,
        "total": 0,
        "ratio": 0.0,
        "started_at": now,
        "updated_at": now,
        "steps": [],
    }


def _recompute(node: Dict[str, Any]) -> None:
    for child in node["steps"]:
        _recompute(child)
    if node["steps"]:
        done, total, ratio = _combine(node["steps"])
        node["done"] = done
        node["total"] = total
        node["ratio"] = 1.0 if node["status"] == "completed" else ratio
        return
    if node["status"] == "completed":
        if node["total"] > 0:
            node["done"] = node["total"]
        node["ratio"] = 1.0
        return
    node["ratio"] = _leaf_ratio(int(node["done"]), int(node["total"]))


def _combine(steps: Sequence[Mapping[str, Any]]) -> Tuple[int, int, float]:
    done = 0
    total = 0
    numerator = 0.0
    denominator = 0.0
    for child in steps:
        weight = float(child.get("weight") or 0)
        if weight <= 0:
            continue
        total += 1
        denominator += weight
        status = str(child.get("status") or "")
        if status in _PASSED:
            numerator += weight
            done += 1
        elif status != "pending":
            numerator += weight * float(child.get("ratio") or 0)
    if denominator <= 0:
        return done, total, 0.0
    return done, total, _round_ratio(numerator / denominator)


def _leaf_ratio(done: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return _round_ratio(done / total)


def _round_ratio(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _collect_ids(node: Mapping[str, Any]) -> List[str]:
    found = [str(node["id"])]
    for child in node.get("steps") or []:
        found.extend(_collect_ids(child))
    return found


def _locate(node_id: str) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]]:
    root_id = _ROOT_OF.get(node_id)
    if root_id is None:
        _refresh_index()
        root_id = _ROOT_OF.get(node_id)
    if root_id is None:
        return None
    root = _BY_ROOT.get(root_id)
    if root is None:
        return None
    found = _walk(root, node_id, [])
    if found is None:
        return None
    node, ancestors = found
    return node, ancestors, root


def _walk(
    node: Dict[str, Any],
    node_id: str,
    ancestors: List[Dict[str, Any]],
) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    if node["id"] == node_id:
        return node, ancestors
    for child in node["steps"]:
        found = _walk(child, node_id, ancestors + [node])
        if found is not None:
            return found
    return None


def _index_tree(root: Dict[str, Any]) -> None:
    root_id = str(root["id"])
    _BY_ROOT[root_id] = root
    for item_id in _collect_ids(root):
        _ROOT_OF[item_id] = root_id


def _drop_index(root_id: str) -> None:
    for item_id, owner in list(_ROOT_OF.items()):
        if owner == root_id:
            del _ROOT_OF[item_id]
    _BY_ROOT.pop(root_id, None)


def _refresh_index() -> None:
    directory = _directory()
    if not directory.is_dir():
        return
    for path in directory.glob("*.json"):
        root_id = path.stem
        if root_id in _BY_ROOT:
            continue
        document = _read_json(path)
        if document is None or str(document.get("id") or "") != root_id:
            continue
        _index_tree(document)


def _prune(*, job: str, keep_root: str) -> None:
    directory = _directory()
    if not directory.is_dir():
        return
    now = time.time()
    finished: List[Tuple[int, str]] = []
    for root_id, root in list(_BY_ROOT.items()):
        if root_id == keep_root or str(root.get("job") or "") != job:
            continue
        if str(root.get("status") or "") not in _TERMINAL:
            continue
        finished.append((_count_loose(root.get("updated_at")), root_id))
    finished.sort(reverse=True)
    for index, (updated_at, root_id) in enumerate(finished):
        age_days = (now - updated_at) / 86400 if updated_at else _KEEP_DAYS + 1
        if index < _KEEP_FILES and age_days <= _KEEP_DAYS:
            continue
        _drop_index(root_id)
        _DIRTY.pop(root_id, None)
        try:
            (directory / f"{root_id}.json").unlink(missing_ok=True)
        except OSError:
            continue


def _publish(root_id: str) -> None:
    snapshot = copy.deepcopy(_BY_ROOT[root_id])
    if _flush_delay() <= 0:
        _write_file(root_id, snapshot)
        return
    _DIRTY[root_id] = snapshot
    _ensure_writer()


def _ensure_writer() -> None:
    global _WRITER_ALIVE
    if _WRITER_ALIVE:
        return
    _WRITER_ALIVE = True
    threading.Thread(target=_writer_loop, name="progress-flush", daemon=True).start()


def _writer_loop() -> None:
    global _WRITER_ALIVE
    while True:
        delay = _flush_delay()
        if delay > 0:
            time.sleep(delay)
        with _LOCK:
            batch = dict(_DIRTY)
            _DIRTY.clear()
            if not batch:
                _WRITER_ALIVE = False
                return
        for root_id, snapshot in batch.items():
            _write_file(root_id, snapshot)


def _write_file(root_id: str, snapshot: Mapping[str, Any]) -> None:
    directory = _directory()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{root_id}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
    except OSError:
        return


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if "id" not in raw or not isinstance(raw.get("steps"), list):
        return None
    return raw


def _directory() -> Path:
    raw = os.environ.get("NTQ_PROGRESS_DIR", "").strip()
    if raw:
        return Path(raw)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / "ntq-progress-pytest"
    try:
        from core.infra.project_context import ProjectContext

        return ProjectContext.path.get_userspace_tmp_directory() / "progress"
    except Exception:
        return Path(tempfile.gettempdir()) / "ntq-progress"


def _flush_delay() -> float:
    raw = os.environ.get("NTQ_PROGRESS_FLUSH_DELAY", "").strip()
    if not raw:
        return _FLUSH_DELAY
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _FLUSH_DELAY


def _print_tick(node: Mapping[str, Any], detail: Optional[str]) -> None:
    text = str(detail).strip() if detail is not None else ""
    if not text:
        label = str(node.get("label") or node.get("id") or "")
        text = f"{label} {node.get('done')}/{node.get('total')}"
    try:
        print(text, flush=True)
    except OSError:
        return


def _check_node_id(node_id: str) -> None:
    if not node_id or node_id in {".", ".."} or "/" in node_id or "\\" in node_id or "\x00" in node_id:
        raise ValueError(f"进度 id 无效: {node_id}")


def _count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"进度 {name} 必须是非负整数")
    if value < 0:
        raise ValueError(f"进度 {name} 必须是非负整数")
    return value


def _count_loose(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


def _weight(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("进度 weight 必须是非负数")
    if value < 0:
        raise ValueError("进度 weight 必须是非负数")
    return float(value)


atexit.register(drain)
