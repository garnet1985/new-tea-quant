"""Strategy 侧 job 进度快照：本模块 channel / file_key 约定；落盘走 ``Progress.channel``。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.progress import Progress


class ProgressRecorder:
    def __init__(self, channel: str, file_key: str):
        self._channel = str(channel).strip()
        self._file_key = str(file_key or "").strip()

    @property
    def recorder_path(self) -> Path:
        return Progress.channel.path(self._channel, self._file_key)

    @staticmethod
    def build_path(channel: str, file_key: str) -> Path:
        return Progress.channel.path(channel, file_key)

    @classmethod
    def for_strategy_workbench_run(
        cls,
        strategy_key: str,
        run_id: str,
        *,
        channel: str = "strategy-workbench-run",
    ) -> "ProgressRecorder":
        """单 job 工作台编排进度：``{strategy}__{run_id}.json``。"""
        sn = str(strategy_key).strip()
        jid = str(run_id).strip()
        return cls(channel, f"{sn}__{jid}")

    @classmethod
    def for_scanner_run(
        cls,
        strategy_key: str,
        run_id: str,
        *,
        channel: str = "strategy-scan",
    ) -> "ProgressRecorder":
        """机会扫描异步任务进度：``{strategy}__{job_id}.json``。"""
        sn = str(strategy_key).strip()
        jid = str(run_id).strip()
        return cls(channel, f"{sn}__{jid}")

    def record(self, progress_template: Dict[str, Any]) -> None:
        Progress.channel.write(self._channel, self._file_key, dict(progress_template or {}))

    def get_progress(self) -> Optional[Dict[str, Any]]:
        return Progress.channel.read(self._channel, self._file_key)

    def reset(self) -> None:
        Progress.channel.clear(self._channel, self._file_key)
