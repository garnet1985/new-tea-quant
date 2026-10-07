from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from core.infra.project_context import ProjectContext

class ProgressRecorder:
    def __init__(self, recorder_path: str | Path):
        self.recorder_path = Path(recorder_path)

    @staticmethod
    def build_path(channel: str, file_key: str) -> Path:
        filename = f"{file_key}.json"
        return ProjectContext.path.get_userspace_tmp_directory() / "progress" / channel / filename

    @classmethod
    def for_strategy_workbench_run(
        cls,
        strategy_name: str,
        run_id: str,
        *,
        channel: str = "strategy-workbench-run",
    ) -> "ProgressRecorder":
        """单 job 工作台编排进度：``{strategy}__{run_id}.json``（与按 step 分文件并存）。"""
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        key = f"{sn}__{jid}"
        return cls(cls.build_path(channel, key))

    @classmethod
    def for_scanner_run(
        cls,
        strategy_name: str,
        run_id: str,
        *,
        channel: str = "strategy-scan",
    ) -> "ProgressRecorder":
        """机会扫描异步任务进度：``{strategy}__{job_id}.json``。"""
        sn = str(strategy_name).strip()
        jid = str(run_id).strip()
        key = f"{sn}__{jid}"
        return cls(cls.build_path(channel, key))

    @classmethod
    def for_tag_run(
        cls,
        tag_key: str,
        run_id: str,
        *,
        channel: str = "tag-run",
    ) -> "ProgressRecorder":
        """Tag UI 异步 run：``{tag_key}__{job_id}.json``（tag_key 可含 ``/``）。"""
        tk = str(tag_key).strip()
        jid = str(run_id).strip()
        key = f"{tk}__{jid}"
        return cls(cls.build_path(channel, key))

    def _atomic_write_json(self, payload: Dict[str, Any]) -> None:
        self.recorder_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.recorder_path.parent,
            delete=False,
        ) as tmp:
            tmp.write(json.dumps(payload, ensure_ascii=False, indent=2))
            tmp_path = Path(tmp.name)
        os.replace(str(tmp_path), str(self.recorder_path))

    def record(self, progress_template: Dict[str, Any]) -> None:
        payload = dict(progress_template)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._atomic_write_json(payload)

    def get_progress(self) -> Optional[Dict[str, Any]]:
        if not self.recorder_path.exists():
            return None
        try:
            payload = json.loads(self.recorder_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            return payload
        except Exception:
            return None

    def reset(self) -> None:
        try:
            self.recorder_path.unlink(missing_ok=True)
        except Exception:
            pass