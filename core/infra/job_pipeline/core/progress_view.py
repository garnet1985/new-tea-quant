"""把 ``infra.progress`` 节点快照压成任务表上的 progress 字段。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

ImportProgressReader = Callable[[], Optional[Dict[str, Any]]]

# 可选：由 BFF / setup 注入，避免 job_pipeline → setup 硬依赖
_import_progress_reader: Optional[ImportProgressReader] = None


def set_import_progress_reader(reader: Optional[ImportProgressReader]) -> None:
    """注册 ``import_data`` 任务的进度读函数（返回与 Setup 导入进度同形的 dict）。"""
    global _import_progress_reader
    _import_progress_reader = reader


def _safe_id(raw: str) -> str:
    return (
        str(raw or "")
        .replace("/", "-")
        .replace("\\", "-")
        .replace("\x00", "")
        .strip()
    )


def progress_root_candidates(job: Dict[str, Any]) -> List[str]:
    """按 kind 推断 Progress 根 id（与业务侧命名对齐）。"""
    jid = str(job.get("job_id") or "").strip()
    if not jid:
        return []
    kind = str(job.get("kind") or "").strip()
    resource = str(job.get("resource_key") or "").strip()
    out: List[str] = []

    def add(value: str) -> None:
        text = _safe_id(value)
        if text and text not in out:
            out.append(text)

    if kind == "tag_run" and resource:
        add(f"tag-{resource}-{jid}")
    # strategy_scan 写 scan-{key}-{jid}（scan_progress），不是 pipeline-*
    if kind == "strategy_scan" and resource:
        add(f"scan-{resource}-{jid}")
    if kind in {
        "strategy_run",
        "strategy_attribute",
        "strategy_rolling",
    } and resource:
        add(f"pipeline-{resource}-{jid}")
    # 设置页 / 安装导入写在固定根 ``import``，不是 job_id。
    if kind == "import_data":
        add("import")
    # data_renew 等直接用 job_id；兜底也试裸 id
    add(jid)
    return out


def _leaf_detail(snap: Dict[str, Any]) -> str:
    """根节点 detail 常为空；取最深 running/paused 叶子的文案。"""
    active = frozenset({"running", "paused"})
    found: Optional[Dict[str, Any]] = None

    def walk(node: Dict[str, Any]) -> None:
        nonlocal found
        if str(node.get("status") or "") in active:
            found = node
        for child in node.get("steps") or []:
            if isinstance(child, dict):
                walk(child)

    walk(snap)
    if found is None:
        return ""
    return str(found.get("detail") or "").strip()


def _snapshot_from_progress_node(raw: Dict[str, Any], *, root_id: str) -> Dict[str, Any]:
    try:
        ratio = float(raw.get("ratio") or 0.0)
    except (TypeError, ValueError):
        ratio = 0.0
    status = str(raw.get("status") or "").strip().lower()
    label = str(raw.get("label") or "").strip()
    detail = str(raw.get("detail") or "").strip() or _leaf_detail(raw)
    return {
        "ratio": max(0.0, min(1.0, ratio)),
        "percent": int(round(max(0.0, min(1.0, ratio)) * 100)),
        "status": status or None,
        "label": label or None,
        "detail": detail or None,
        "updated_at": raw.get("updated_at"),
        "started_at": raw.get("started_at"),
        "root_id": root_id,
    }


def _snapshot_from_import_progress() -> Optional[Dict[str, Any]]:
    """与设置页同一数据源，避免只认 Progress 根 id 时管道空白。"""
    reader = _import_progress_reader
    if reader is None:
        return None
    try:
        ip = reader()
    except Exception:
        return None
    if not isinstance(ip, dict) or not ip.get("running"):
        return None
    try:
        ratio = float(ip.get("ratio") or 0.0)
    except (TypeError, ValueError):
        ratio = 0.0
    phase = str(ip.get("phase") or "").strip()
    detail = str(ip.get("statusText") or "").strip()
    if not detail:
        if phase == "downloading":
            detail = "数据下载中…"
        elif phase == "preparing":
            detail = "准备导入…"
        elif int(ip.get("totalTables") or 0) > 0:
            cur = str(ip.get("currentTable") or "").strip()
            detail = (
                f"正在导入 {int(ip.get('completedCount') or 0)}/"
                f"{int(ip.get('totalTables') or 0)}"
                + (f"：{cur}" if cur else "")
            )
        else:
            detail = "正在导入数据…"
    return {
        "ratio": max(0.0, min(1.0, ratio)),
        "percent": int(round(max(0.0, min(1.0, ratio)) * 100)),
        "status": "running",
        "label": "导入数据",
        "detail": detail or None,
        "updated_at": None,
        "started_at": None,
        "root_id": "import",
    }


def read_progress_snapshot_for_job(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """按任务快照解析 Progress 根并压成摘要。"""
    try:
        from core.infra.progress import Progress
    except Exception:
        Progress = None  # type: ignore[assignment]
    if Progress is not None:
        for root in progress_root_candidates(job):
            try:
                raw = Progress.read(root)
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            return _snapshot_from_progress_node(raw, root_id=root)
    if str(job.get("kind") or "").strip() == "import_data":
        return _snapshot_from_import_progress()
    return None


def attach_progress(job: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """给任务快照挂上 progress；已有非空 progress 则不覆盖。"""
    if not isinstance(job, dict):
        return job
    out = dict(job)
    existing = out.get("progress")
    if isinstance(existing, dict) and existing:
        return out
    snap = read_progress_snapshot_for_job(out)
    if snap is not None:
        out["progress"] = snap
    return out
