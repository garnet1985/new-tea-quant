"""Runner implementer: workbench run + scan (launcher wrappers)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.core.enums import WorkbenchStep
from core.modules.strategy.core.services.discovery import DiscoveryService


class StrategyRunnerImplementer:
    def __init__(self) -> None:
        self._WorkbenchRunLauncher = None
        self._get_scan_page_context = None
        self._get_scan_readiness = None
        self._get_scan_progress = None
        self._trigger_strategy_scan_run = None

    def lazy_load(self) -> "StrategyRunnerImplementer":
        if self._WorkbenchRunLauncher is None:
            from core.modules.strategy.launcher.scanner_run import (
                get_scan_page_context,
                get_scan_progress,
                get_scan_readiness,
                trigger_strategy_scan_run,
            )
            from core.modules.strategy.launcher.workbench_run import WorkbenchRunLauncher

            self._WorkbenchRunLauncher = WorkbenchRunLauncher
            self._get_scan_page_context = get_scan_page_context
            self._get_scan_readiness = get_scan_readiness
            self._get_scan_progress = get_scan_progress
            self._trigger_strategy_scan_run = trigger_strategy_scan_run
        return self

    @staticmethod
    def resolve_strategy_name(strategy_key_or_name: str) -> str:
        return DiscoveryService.resolve_strategy_path(strategy_key_or_name)

    @staticmethod
    def normalize_step(step: str) -> Optional[str]:
        parsed = WorkbenchStep.try_parse(step)
        return parsed.value if parsed is not None else None

    def submit_run(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        api_settings: Dict[str, Any],
        force_refresh: bool,
    ) -> Dict[str, Any]:
        assert self._WorkbenchRunLauncher is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        return self._WorkbenchRunLauncher.submit(
            strategy_name=name,
            step=step,
            api_settings=api_settings,
            force_refresh=bool(force_refresh),
        )

    def get_run_progress(
        self, *, strategy_key_or_name: str, job_id: str
    ) -> Optional[Dict[str, Any]]:
        assert self._WorkbenchRunLauncher is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        return self._WorkbenchRunLauncher.get_run_progress(
            strategy_name=name, job_id=job_id
        )

    def get_step_progress(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        assert self._WorkbenchRunLauncher is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        norm = StrategyRunnerImplementer.normalize_step(step)
        if norm is None:
            raise ValueError("step 须为 enum / price / portfolio")
        return self._WorkbenchRunLauncher.get_step_progress(
            strategy_name=name,
            normalized_step=norm,
            job_id=job_id,
        )

    def scan_page_context(self) -> Dict[str, Any]:
        assert self._get_scan_page_context is not None
        return self._get_scan_page_context()

    def scan_readiness(
        self, *, strategy_key_or_name: str, demo: bool
    ) -> Dict[str, Any]:
        assert self._get_scan_readiness is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        return self._get_scan_readiness(strategy_name=name, demo=bool(demo))

    def trigger_scan(
        self, *, strategy_key_or_name: str, demo: bool, force: bool
    ) -> Dict[str, Any]:
        assert self._trigger_strategy_scan_run is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        return self._trigger_strategy_scan_run(
            strategy_name=name, demo=bool(demo), force=bool(force)
        )

    def scan_progress(
        self, *, strategy_key_or_name: str, job_id: str
    ) -> Optional[Dict[str, Any]]:
        assert self._get_scan_progress is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        return self._get_scan_progress(strategy_name=name, job_id=job_id)


impl = StrategyRunnerImplementer()
