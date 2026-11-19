"""读标签进度与性能报告摘要（只经 Tag Facade + 本机报告文件）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder
from core.modules.tag import Tag

_SUMMARY_FIELDS = (
    "wall_clock_seconds",
    "total_jobs",
    "ok_jobs",
    "failed_jobs",
    "tag_values_count",
    "saved_tag_values",
    "dry_run",
    "entity_count",
)


def tag_progress(key: str, task_id: str) -> Dict[str, Any]:
    """供 read_progress 在 kind=tag 时调用。"""
    doc = Tag.get_run_progress(tag_key=key, job_id=task_id)
    if not doc:
        return {"ok": False, "key": key, "task_id": task_id, "error": "进度不存在"}
    status = str(doc.get("status") or "").strip()
    out: Dict[str, Any] = {
        "ok": True,
        "key": key,
        "task_id": task_id,
        "kind": "tag",
        "status": status,
        "progress": doc.get("progress"),
        "step": str(doc.get("label") or ""),
    }
    if doc.get("reason"):
        out["error"] = str(doc.get("reason"))
    if status not in {"completed", "failed", "cancelled"}:
        out["note"] = "尚未结束。不要编写结果数字"
    return out


def list_tag_summaries(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """列出本机标签及最新性能报告摘要。"""
    if not isinstance(arguments, dict) or set(arguments):
        return {"ok": False, "error": "不接受额外参数"}
    try:
        infos = Tag.list_tag_infos(enabled_only=False)
    except Exception as exc:
        return {"ok": False, "error": f"无法列出标签: {exc}"}

    items: List[Dict[str, Any]] = []
    for info in infos:
        path_id = str(info.get("unique_relative_path") or "")
        report = _latest_report(path_id)
        summary: Dict[str, Any] = {}
        version_id = None
        if report:
            version_id = report.get("version_id")
            raw = report.get("summary") if isinstance(report.get("summary"), dict) else {}
            summary = {name: raw.get(name) for name in _SUMMARY_FIELDS if name in raw}
        items.append(
            {
                "key": info.get("key") or path_id,
                "path": path_id,
                "display_name": info.get("display_name") or None,
                "is_enabled": bool(info.get("is_enabled")),
                "version_id": version_id,
                "summary": summary,
            }
        )
    return {"ok": True, "count": len(items), "items": items}


def read_tag_report(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """读取标签性能报告摘要。"""
    allowed = {"key", "version_id"}
    if not isinstance(arguments, dict) or not set(arguments) <= allowed:
        return {"ok": False, "error": "只接受参数 key、version_id"}
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    parsed = parse_tag_key({"key": arguments.get("key")}, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"标签不存在: {relative}"}

    version = str(arguments.get("version_id") or "").strip()
    report = _report_at(parsed, version) if version else _latest_report(parsed)
    if not report:
        info = Tag.get_tag_info(parsed, enabled_only=False)
        path_id = str((info or {}).get("unique_relative_path") or parsed)
        report = _report_at(path_id, version) if version else _latest_report(path_id)
    if not report:
        return {
            "ok": False,
            "key": parsed,
            "error": "没有找到标签性能报告。请先 start_tag",
        }
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    picked = {name: summary.get(name) for name in _SUMMARY_FIELDS if name in summary}
    return {
        "ok": True,
        "key": parsed,
        "kind": "tag",
        "version_id": report.get("version_id"),
        "execution_mode": report.get("execution_mode"),
        "summary": picked,
        "note": "数字只来自本摘要；不要编造未列出的指标。",
    }


def _latest_report(path_id: str) -> Optional[Dict[str, Any]]:
    root = _performance_root(path_id)
    if root is None or not root.is_dir():
        return None
    versions: List[int] = []
    for child in root.iterdir():
        if child.is_dir() and child.name.isdigit():
            versions.append(int(child.name))
    if not versions:
        return None
    return _load_report(root / str(max(versions)), max(versions))


def _report_at(path_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    if not version_id.isdigit():
        return None
    root = _performance_root(path_id)
    if root is None:
        return None
    return _load_report(root / version_id, int(version_id))


def _performance_root(path_id: str) -> Optional[Path]:
    needle = str(path_id or "").strip().strip("/")
    if not needle:
        return None
    return ProjectContext.path.get_tags_root() / needle / "results" / "performance"


def _load_report(version_dir: Path, version_id: int) -> Optional[Dict[str, Any]]:
    path = version_dir / "0_performance_report.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    payload = dict(payload)
    payload["version_id"] = version_id
    return payload
