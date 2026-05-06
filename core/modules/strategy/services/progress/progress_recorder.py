from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from core.infra.project_context.path_manager import PathManager


class ProgressRecorder:
    def __init__(self, recorder_path: str | Path):
        self.recorder_path = Path(recorder_path)

    @staticmethod
    def build_path(channel: str, file_key: str) -> Path:
        filename = f"{file_key}.json"
        return PathManager.userspace_tmp() / "progress" / channel / filename

    @classmethod
    def for_strategy_run_step(
        cls,
        strategy_name: str,
        run_id: str,
        step_name: str,
        *,
        channel: str = "strategy-workbench",
    ) -> "ProgressRecorder":
        key = f"{strategy_name}__{run_id}__{step_name}"
        return cls(cls.build_path(channel, key))

    @classmethod
    def for_scanner_run(
        cls,
        strategy_name: str,
        run_id: str,
        *,
        channel: str = "scanner",
    ) -> "ProgressRecorder":
        key = f"{strategy_name}__{run_id}__scan"
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