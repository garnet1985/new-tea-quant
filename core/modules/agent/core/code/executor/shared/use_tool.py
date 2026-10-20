"""Executor 共用：执行工具；启动类任务等到终态再返回。"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from core.modules.agent.core.code.conf.conf import (
    TOOL_AWAIT_SECONDS,
    TOOL_POLL_INTERVAL_SECONDS,
)
from core.modules.agent.core.code.tools.strategy.read_reports import read_progress
from core.modules.agent.core.code.tools.tool_catalog import ToolCatalog
from core.modules.agent.core.code.tools.tool_runner import run_tool

logger = logging.getLogger(__name__)


def use_tool(
    catalog: ToolCatalog,
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = run_tool(catalog, name, arguments)
    if result.get("task_id") and result.get("status") == "running":
        return _await_task(result)
    return result


def _await_task(result: Dict[str, Any]) -> Dict[str, Any]:
    task_id = str(result.get("task_id") or "").strip()
    deadline = time.monotonic() + TOOL_AWAIT_SECONDS
    latest = dict(result)
    seen = ""
    while time.monotonic() < deadline:
        time.sleep(TOOL_POLL_INTERVAL_SECONDS)
        progress = read_progress({"task_id": task_id})
        latest = {**result, **progress}
        status = str(progress.get("status") or "")
        marker = f"{status} {progress.get('progress')} {progress.get('step')}"
        if marker != seen:
            seen = marker
            logger.info("任务 %s：%s", task_id, marker)
        if status in {"completed", "failed", "cancelled"}:
            if status == "completed" and progress.get("kind") != "scan":
                latest["note"] = "任务已结束。接着读执行报告，数字只能来自报告。"
            return latest
    latest["note"] = "等待超时，任务可能仍在跑。不要编写结果数字。"
    return latest
