"""本机任务记录：task_id 对应策略与进度 id。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from core.infra.project_context import ProjectContext

_TASK_ID = re.compile(r"^[a-z]{3,8}-[a-f0-9]{12}$")


def tasks_directory() -> Path:
    return ProjectContext.path.get_userspace_ntq_directory() / "agent" / "tasks"


def write_task(record: Dict[str, Any]) -> None:
    task_id = str(record.get("task_id") or "")
    if not _TASK_ID.fullmatch(task_id):
        raise ValueError("task_id 无效")
    directory = tasks_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{task_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def task_file(task_id: str) -> Path:
    return tasks_directory() / f"{task_id}.json"
