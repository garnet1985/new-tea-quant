"""后台启动标签计算。模型只提交 key，任务立刻返回（异步壳在 agent，对齐 strategy）。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError
from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder
from core.modules.agent.core.code.tools.tag.validate_tag import validate_tag
from core.modules.agent.core.code.tools.task_record import write_task
from core.modules.tag import Tag

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ACTIVE: Dict[str, str] = {}


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

    task_id = f"tag-{uuid.uuid4().hex[:12]}"
    if not _claim(gated, task_id):
        return {"ok": False, "key": gated, "error": "该标签已有任务在运行"}

    try:
        Tag.seed_run_progress(gated, task_id)
        write_task({"task_id": task_id, "key": gated, "kind": "tag"})
    except Exception as exc:
        _release(gated, task_id)
        logger.exception("seed tag failed key=%s", gated)
        return {"ok": False, "key": gated, "error": f"无法登记标签任务: {exc}"}

    thread = threading.Thread(
        target=_worker,
        args=(gated, task_id),
        daemon=True,
        name=f"ntq-tag-{task_id[-6:]}",
    )
    thread.start()
    return {
        "ok": True,
        "key": gated,
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


def _claim(key: str, task_id: str) -> bool:
    with _LOCK:
        if _ACTIVE.get(key):
            return False
        _ACTIVE[key] = task_id
        return True


def _release(key: str, task_id: str) -> None:
    with _LOCK:
        if _ACTIVE.get(key) == task_id:
            _ACTIVE.pop(key, None)


def _worker(key: str, task_id: str) -> None:
    lease = JobPipeline.running_lease(
        kind="tag_run",
        job_id=task_id,
        resource_key=key,
        label=f"Tag: {key}",
        domains=["data", "tag"],
    )
    try:
        lease.acquire()
    except JobRunningBusyError as exc:
        Tag.fail_run_progress(key, task_id, str(exc))
        _release(key, task_id)
        JobPipeline.notify_job_finished()
        return

    try:
        Tag.mark_run_running(key, task_id)
        if JobPipeline.is_cancel_requested(task_id):
            Tag.fail_run_progress(key, task_id, "用户取消")
            return
        base_cb = Tag.run_progress_callback(key, task_id)

        def _on_progress(*args, **kwargs):
            if JobPipeline.is_cancel_requested(task_id):
                raise RuntimeError("用户取消")
            if callable(base_cb):
                return base_cb(*args, **kwargs)
            return None

        result = Tag(is_verbose=False).execute(
            scenario_name=key,
            on_pipeline_progress=_on_progress,
        )
        if JobPipeline.is_cancel_requested(task_id):
            Tag.fail_run_progress(key, task_id, "用户取消")
            return
        _require_successful_run(result)
        Tag.complete_run_progress(key, task_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("tag run failed key=%s task=%s", key, task_id)
        Tag.fail_run_progress(key, task_id, str(exc))
    finally:
        try:
            lease.release()
        except Exception:
            logger.exception("lease release failed task=%s", task_id)
        _release(key, task_id)
        JobPipeline.notify_job_finished()


def _require_successful_run(result: Any) -> None:
    if not isinstance(result, dict) or not result.get("success"):
        message = ""
        if isinstance(result, dict):
            message = str(result.get("message") or "").strip()
            failed = int(result.get("fail") or 0)
            if not message and failed:
                message = f"标签计算失败（{failed} 个任务）"
        raise RuntimeError(message or "标签计算未完成")
    if result.get("dry_run"):
        return
    produced = int(result.get("tag_values_count") or 0)
    saved = int(result.get("saved_tag_values") or 0)
    if produced > 0 and saved < produced:
        raise RuntimeError(
            f"标签值未全部落库（计算 {produced} 行，写入 {saved} 行）"
        )
