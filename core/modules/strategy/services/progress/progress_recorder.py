from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import AbstractSet, Any, Dict, Optional

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
    def clear_workspace_runs_for_strategy_step(
        cls,
        strategy_name: str,
        step_name: str,
        *,
        channel: str = "strategy-workbench",
        preserve_run_ids: Optional[AbstractSet[str]] = None,
    ) -> None:
        """删除该策略、该 step 下已不再需要的进度文件（``{strategy}__*__{step}.json``）。

        供定时任务、清缓存按钮等 infra 调用；工作台异步 run 不在此处触发清理。

        ``preserve_run_ids``：仍应保留的 ``job_id``（例如仍为 queued/running 的任务）。
        """
        sn = str(strategy_name).strip()
        step = str(step_name).strip()
        if not sn or not step:
            return
        keep = preserve_run_ids or set()
        d = PathManager.userspace_tmp() / "progress" / channel
        if not d.is_dir():
            return
        prefix = f"{sn}__"
        suffix = f"__{step}.json"
        for p in d.iterdir():
            try:
                if not p.is_file() or not p.name.startswith(prefix) or not p.name.endswith(suffix):
                    continue
                rid = p.name[len(prefix) : -len(suffix)]
                if rid in keep:
                    continue
                p.unlink(missing_ok=True)
            except OSError:
                pass

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