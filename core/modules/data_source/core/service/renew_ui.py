"""Renew UI 进度 DTO（任务栏 + Progress 树投影）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def read_renew_ui_tasks() -> List[Dict[str, Any]]:
    """最近一次运行的任务栏，只留界面字段。"""
    from core.modules.data_source.core.service.run_status import read_latest_run_status

    payload = read_latest_run_status()
    raw = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []
    tasks: List[Dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        tasks.append(
            {
                "source": str(row.get("source") or ""),
                "status": str(row.get("status") or ""),
                "started_at": row.get("started_at"),
                "total_seconds": row.get("total_seconds"),
                "error": str(row.get("error") or ""),
            }
        )
    return tasks


def read_renew_ui_progress() -> Dict[str, Any]:
    """当前 renew Progress：step 为源计数，sub 为正在跑的那一个。"""
    from core.infra.progress import Progress

    snap = Progress.latest("renew")
    if not isinstance(snap, dict):
        return _empty_progress()
    current = _deepest_running(snap)
    leaf = current if current and current.get("id") != snap.get("id") else None
    return {
        "job": str(snap.get("job") or ""),
        "source": str((leaf or {}).get("source") or ""),
        "step": int(snap.get("done") or 0),
        "step_total": int(snap.get("total") or 0),
        "sub": int((leaf or {}).get("done") or 0),
        "sub_total": int((leaf or {}).get("total") or 0),
        "updated_at": int(snap.get("updated_at") or 0),
        "ratio": float(snap.get("ratio") or 0),
        "status": str(snap.get("status") or ""),
        "label": str((leaf or snap).get("label") or ""),
        "detail": str((leaf or {}).get("detail") or ""),
    }


def read_renew_ui_status() -> Dict[str, Any]:
    """任务栏 + 进度（不含 BFF 本地 _ACTIVE / JobPipeline running）。"""
    return {
        "tasks": read_renew_ui_tasks(),
        "progress": read_renew_ui_progress(),
    }


def _empty_progress() -> Dict[str, Any]:
    return {
        "job": "",
        "source": "",
        "step": 0,
        "step_total": 0,
        "sub": 0,
        "sub_total": 0,
        "updated_at": 0,
        "ratio": 0,
        "status": "",
        "label": "",
        "detail": "",
    }


def _deepest_running(node: dict) -> Optional[dict]:
    from core.infra.progress import Progress

    return Progress.tree.deepest(node, frozenset({"running"}))
