"""Attribution implementer: status / run / progress / report."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy import Strategy
from core.modules.strategy.contracts import WorkbenchStep


class StrategyAttributionImplementer:
    def __init__(self) -> None:
        self._AttributeRunLauncher = None
        self._AttributeStatus = None
        self._AttributeReportReader = None

    def lazy_load(self) -> "StrategyAttributionImplementer":
        if self._AttributeRunLauncher is None:
            from core.bff.APIs.strategy.routes.attribution.attribute_run import (
                AttributeRunLauncher,
            )
            from core.bff.APIs.strategy.routes.attribution.report import (
                AttributeReportReader,
            )
            from core.bff.APIs.strategy.routes.attribution.status import (
                AttributeStatus,
            )

            self._AttributeRunLauncher = AttributeRunLauncher
            self._AttributeStatus = AttributeStatus
            self._AttributeReportReader = AttributeReportReader
        return self

    @staticmethod
    def normalize_step(step: str) -> Optional[str]:
        parsed = WorkbenchStep.try_parse(step)
        return parsed.value if parsed is not None else None

    def status(
        self, *, strategy_key_or_name: str, step: str
    ) -> Dict[str, Any]:
        assert self._AttributeStatus is not None
        name = Strategy.resolve(strategy_key_or_name)
        norm = self.normalize_step(step)
        if norm is None:
            raise ValueError("step 须为 enum / price / portfolio")
        return self._AttributeStatus.probe(name, norm)

    def submit_run(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        force_refresh: bool,
    ) -> Dict[str, Any]:
        assert self._AttributeRunLauncher is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._AttributeRunLauncher.submit(
            strategy_name=name,
            step=step,
            force_refresh=bool(force_refresh),
        )

    def get_run_progress(
        self, *, strategy_key_or_name: str, job_id: str
    ) -> Optional[Dict[str, Any]]:
        assert self._AttributeRunLauncher is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._AttributeRunLauncher.get_run_progress(
            strategy_name=name, job_id=job_id
        )

    def build_report(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        group_id: str,
    ) -> Dict[str, Any]:
        assert self._AttributeReportReader is not None
        name = Strategy.resolve(strategy_key_or_name)
        norm = self.normalize_step(step)
        if norm is None:
            raise ValueError("step 须为 enum / price / portfolio")
        return self._AttributeReportReader.build(
            strategy_name=name,
            normalized_step=norm,
            group_id=group_id,
        )


impl = StrategyAttributionImplementer()
