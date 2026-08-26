"""Post-simulate analyze triggers and version backfill."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.modules.strategy.core.enums import WorkbenchStep
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)

from ..support.paths import AnalyzerPaths
from ..support.step_mapping import AnalyzerStepMapping
from .pipeline import AnalyzerPipeline

logger = logging.getLogger(__name__)

_STEP_RESULT_KEYS = {
    WorkbenchStep.ENUM: "enumerate",
    WorkbenchStep.PRICE: "price_factor",
    WorkbenchStep.PORTFOLIO: "portfolio",
}


class AnalyzerAutoRun:
    @staticmethod
    def is_enabled(settings: Dict[str, Any]) -> bool:
        block = settings.get("analysis")
        if not isinstance(block, dict):
            return False
        enabled = block.get("enabled", False)
        return bool(enabled) if isinstance(enabled, bool) else False

    @staticmethod
    def extract_step_result(
        simulate_result: Dict[str, Any],
        step: WorkbenchStep,
    ) -> Optional[Dict[str, Any]]:
        key = _STEP_RESULT_KEYS[step]
        nested = simulate_result.get(key)
        if isinstance(nested, dict):
            return nested
        if simulate_result.get("output_dir") or simulate_result.get("version_id"):
            return simulate_result
        return None

    @classmethod
    def maybe_after_simulate(
        cls,
        strategy_key: str,
        *,
        step: str,
        simulate_result: Dict[str, Any],
        effective_settings: Dict[str, Any],
        force: bool = False,
    ) -> Dict[str, Any]:
        if not cls.is_enabled(effective_settings):
            return {"skipped": True, "reason": "disabled"}

        workbench_step = AnalyzerStepMapping.parse(step)
        step_result = cls.extract_step_result(simulate_result, workbench_step)
        if not step_result:
            return {"skipped": True, "reason": "missing_step_result"}
        if step_result.get("success") is False:
            return {"skipped": True, "reason": "simulate_failed"}

        output_dir = str(step_result.get("output_dir") or "").strip()
        version_id = str(step_result.get("version_id") or "").strip()
        if not output_dir and not version_id:
            return {"skipped": True, "reason": "missing_version"}

        if output_dir and AnalyzerPaths.report_ready(Path(output_dir)) and not force:
            return {"skipped": True, "reason": "exists"}

        try:
            from core.modules.strategy.core.services.artifacts import ArtifactStore
            from core.modules.strategy.core.services.discovery import DiscoveryService

            folder = DiscoveryService.resolve_strategy_folder(strategy_key)
            simulate_kind = workbench_step.to_simulate_kind()
            if version_id:
                store = ArtifactStore.resolve(
                    folder, kind=simulate_kind, version_id=version_id
                )
            elif output_dir:
                store = ArtifactStore.open(
                    Path(output_dir),
                    kind=simulate_kind,
                )
            else:
                return {"skipped": True, "reason": "missing_version"}
            result = AnalyzerPipeline.run(store)
            return {"skipped": False, **result}
        except Exception as exc:
            logger.exception(
                "analysis auto-run failed: strategy=%s step=%s",
                strategy_key,
                workbench_step.value,
            )
            return {"skipped": True, "reason": "error", "error": str(exc)}

    @classmethod
    def ensure_version(
        cls,
        strategy_key: str,
        *,
        version_id: str,
        effective_settings: Dict[str, Any],
        force: bool = False,
    ) -> Dict[str, Any]:
        if not cls.is_enabled(effective_settings):
            return {"skipped": True, "reason": "disabled"}

        vid = str(version_id or "").strip().lstrip("vV")
        if not vid:
            return {"skipped": True, "reason": "missing_version"}

        from core.modules.strategy.core.services.artifacts import ArtifactStore
        from core.modules.strategy.core.services.artifacts.version_meta import (
            VersionMetaStore,
        )
        from core.modules.strategy.core.services.discovery import DiscoveryService

        try:
            folder = DiscoveryService.resolve_strategy_folder(strategy_key)
        except Exception:
            return {"skipped": True, "reason": "strategy_not_found"}

        root = ArtifactStore.simulations_root(folder)
        if VersionMetaStore.resolve_version(root, vid) is None:
            return {"skipped": True, "reason": "missing_version"}

        ran: list[str] = []
        already: list[str] = []
        errors: list[Dict[str, str]] = []
        for workbench_step in WorkbenchStep:
            kind = workbench_step.to_simulate_kind()
            if not VersionMetaStore.step_has_artifacts(root, vid, kind):
                continue
            try:
                store = ArtifactStore.resolve(folder, kind=kind, version_id=vid)
            except FileNotFoundError:
                continue
            out_dir = Path(store.output_dir)
            if AnalyzerPaths.report_ready(out_dir) and not force:
                already.append(workbench_step.value)
                continue
            try:
                AnalyzerPipeline.run(store)
                ran.append(workbench_step.value)
            except Exception as exc:
                logger.exception(
                    "analysis backfill failed: strategy=%s version=%s step=%s",
                    strategy_key,
                    vid,
                    workbench_step.value,
                )
                errors.append({"step": workbench_step.value, "error": str(exc)})

        if not ran and not errors:
            return {"skipped": True, "reason": "nothing_todo", "already": already}
        return {"skipped": False, "ran": ran, "already": already, "errors": errors}

    @staticmethod
    def effective_settings_for_strategy(
        strategy_key: str,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from core.modules.strategy.core.services.discovery import DiscoveryService

        info = DiscoveryService.find_strategy(strategy_key)
        if info is None:
            return {}
        disk = dict(info.settings or {})
        effective, _ = StrategySettings.calculate_effective_settings(
            disk,
            dict(runtime_settings or {}),
        )
        return dict(effective.raw_settings)
