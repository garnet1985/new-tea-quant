"""后台启动标签计算。模型只提交 key，任务立刻返回。"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.infra.job_pipeline import JobPipeline
from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder
from core.modules.agent.core.code.tools.tag.validate_tag import validate_tag
from core.modules.agent.core.code.tools.task_record import write_task
from core.modules.tag import Tag

logger = logging.getLogger(__name__)


def start_tag(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """对已启用且通过校验的标签启动计算，并立刻返回。"""
    gated = _gate(arguments)
    if isinstance(gated, dict):
        return gated

    running = JobPipeline.get_running_job()
    if running:
        kind = str(running.get("kind") or "unknown")
        return {
            "ok": False,
            "key": gated,
            "error": f"系统任务进行中（{kind}），请稍后再试",
        }

    out = Tag.start_run(tag_key=gated)
    if not out.get("is_triggered"):
        return {
            "ok": False,
            "key": gated,
            "error": str(out.get("reason") or "无法启动标签计算"),
        }
    task_id = str(out.get("job_id") or "").strip()
    run_key = str(out.get("tag_key") or gated).strip()
    if not task_id:
        return {"ok": False, "key": gated, "error": "启动成功但缺少 job_id"}
    try:
        write_task({"task_id": task_id, "key": run_key, "kind": "tag"})
    except Exception as exc:
        logger.exception("write tag task failed key=%s", run_key)
        return {"ok": False, "key": run_key, "error": f"无法登记标签任务: {exc}"}
    return {
        "ok": True,
        "key": run_key,
        "task_id": task_id,
        "status": "running",
        "kind": "tag",
        "note": "打标已启动。不要等待结束，也不要在进度完成前编写结果数字",
    }


def _gate(arguments: Dict[str, Any]) -> str | Dict[str, Any]:
    parsed = parse_tag_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"标签不存在: {relative}。请先 create_tag"}

    checked = validate_tag({"key": parsed})
    if not checked.get("ok"):
        return {
            "ok": False,
            "key": parsed,
            "error": "标签尚未通过校验，没有启动打标",
            "errors": checked.get("errors") or [checked.get("error") or "校验失败"],
        }

    info = Tag.get_tag_info(parsed, enabled_only=False)
    if info is None or not info.get("is_enabled"):
        return {"ok": False, "key": parsed, "error": f"标签不存在或未启用: {parsed}"}
    return str(info.get("unique_relative_path") or parsed)
