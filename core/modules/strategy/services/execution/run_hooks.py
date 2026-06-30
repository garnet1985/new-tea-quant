#!/usr/bin/env python3
"""Main-process run lifecycle hooks for BacktestEngine integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.hooks import (
    StrategyHookRuntime,
    batch_context,
    run_context,
)


class StrategyRunHooksCoordinator:
    """在 enum / scanner 等 flow 主进程阶段调用用户 hooks。"""

    def __init__(
        self,
        runtime: StrategyHookRuntime,
        *,
        run_name: str,
        output_dir: Optional[Path],
        total_entities: int,
        execution_mode: str,
    ) -> None:
        self.runtime = runtime
        self.run_name = run_name
        self.output_dir = output_dir
        self.total_entities = total_entities
        self.execution_mode = execution_mode

    @classmethod
    def from_job(
        cls,
        job: Dict[str, Any],
        *,
        run_name: str,
        output_dir: Optional[Path],
        total_entities: int,
        execution_mode: str,
    ) -> StrategyRunHooksCoordinator:
        settings = StrategySettingsView.from_dict(job["settings"])
        runtime = StrategyHookRuntime.from_job_payload(job, settings=settings)
        return cls(
            runtime,
            run_name=run_name,
            output_dir=output_dir,
            total_entities=total_entities,
            execution_mode=execution_mode,
        )

    def _run_ctx(self):
        return run_context(
            strategy_name=self.runtime.strategy_name,
            settings=self.runtime.settings,
            run_name=self.run_name,
            output_dir=self.output_dir,
            total_entities=self.total_entities,
            execution_mode=self.execution_mode,
        )

    def on_run_start(self) -> None:
        self.runtime.call_if_overridden("on_run_start", self._run_ctx())

    def on_run_finish(self) -> None:
        self.runtime.call_if_overridden("on_run_finish", self._run_ctx())

    def on_batch_start(self, batch_job_id: str, stock_ids: List[str]) -> None:
        ctx = batch_context(
            strategy_name=self.runtime.strategy_name,
            settings=self.runtime.settings,
            batch_job_id=batch_job_id,
            stock_ids=stock_ids,
        )
        self.runtime.call_if_overridden("on_batch_start", ctx)

    def on_batch_finish(
        self,
        batch_job_id: str,
        stock_ids: List[str],
        *,
        report: Any = None,
        progress: Any = None,
    ) -> None:
        ctx = batch_context(
            strategy_name=self.runtime.strategy_name,
            settings=self.runtime.settings,
            batch_job_id=batch_job_id,
            stock_ids=stock_ids,
            report=report,
            progress=progress,
        )
        self.runtime.call_if_overridden("on_batch_finish", ctx)


__all__ = ["StrategyRunHooksCoordinator"]
