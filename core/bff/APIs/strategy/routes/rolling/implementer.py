"""滚动对照接口的实现：状态、启动、进度、报告。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy import Strategy


class StrategyRollingImplementer:
    """延迟加载滚动对照的状态、启动和报告。"""

    def __init__(self) -> None:
        self._RollingRunLauncher = None
        self._probe = None
        self._RollingReportReader = None

    def lazy_load(self) -> "StrategyRollingImplementer":
        """第一次调用时载入具体实现。"""
        if self._RollingRunLauncher is None:
            from core.bff.APIs.strategy.routes.rolling.report import RollingReportReader
            from core.bff.APIs.strategy.routes.rolling.rolling_run import (
                RollingRunLauncher,
            )
            from core.modules.strategy.core.engines.rolling.readiness import probe

            self._RollingRunLauncher = RollingRunLauncher
            self._RollingReportReader = RollingReportReader
            self._probe = probe
        return self

    def status(self, *, strategy_key_or_name: str) -> Dict[str, Any]:
        """查询滚动测试按钮是否可点。"""
        assert self._probe is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._probe(name)

    def submit_run(
        self,
        *,
        strategy_key_or_name: str,
        force_refresh: bool,
    ) -> Dict[str, Any]:
        """启动滚动对照。"""
        assert self._RollingRunLauncher is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._RollingRunLauncher.submit(
            strategy_name=name,
            force_refresh=bool(force_refresh),
        )

    def get_run_progress(
        self, *, strategy_key_or_name: str, job_id: str
    ) -> Optional[Dict[str, Any]]:
        """读取一次滚动对照任务的进度。"""
        assert self._RollingRunLauncher is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._RollingRunLauncher.get_run_progress(
            strategy_name=name, job_id=job_id
        )

    def build_report(self, *, strategy_key_or_name: str) -> Dict[str, Any]:
        """读取已落盘的滚动报告。"""
        assert self._RollingReportReader is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._RollingReportReader.build(strategy_name=name)


impl = StrategyRollingImplementer()
