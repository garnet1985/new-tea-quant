"""按 execute_fp 查已有 version；miss 且 fill_missing 时再 Strategy.simulate。"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    SimulationVersionStore,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.services.entity_loader.sample_list_resolver import (
    SampleListResolver,
)
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator, FingerprintResult
from core.modules.strategy.core.services.package.settings_loader import (
    load_settings_dict_from_folder,
)

from .cells import AttributionTask

logger = logging.getLogger(__name__)

_SampleKey = Tuple[str, str, Tuple[str, ...]]


@dataclass(frozen=True)
class CellExecuteResult:
    """一格的缓存命中 / 跳过 / 补跑结果。"""

    index: int
    status: str
    version_id: Optional[str] = None
    execute_fp: Optional[str] = None
    env_fp: Optional[str] = None
    output_dir: Optional[str] = None
    reason: str = ""


class ExecuteStep:
    """战役执行：先复用磁盘 version，默认不补跑。命中/补跑的号立刻钉住。"""

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        config: Any,
    ) -> Dict[str, Any]:
        strategy_info = cls._resolve_strategy_info(folder)
        snapshot_sample = None
        if any(task.cell.is_select for task in tasks):
            snapshot_sample = cls._snapshot_sample(folder, strategy_info)
        rows: List[CellExecuteResult] = [
            cls._run_one(folder, strategy_info, task, snapshot_sample)
            for task in tasks
        ]
        hits = [row.index for row in rows if row.status == "hit"]
        simulated = [row.index for row in rows if row.status == "simulated"]
        skipped = [row.index for row in rows if row.status == "skipped"]
        return {
            "status": "ok",
            "folder": str(Path(folder).resolve()),
            "fill_missing": config.fill_missing,
            "task_count": len(tasks),
            "hits": hits,
            "simulated": simulated,
            "skipped": skipped,
            "misses": skipped,
            "cells": [asdict(row) for row in rows],
        }

    @classmethod
    def _run_one(
        cls,
        folder: Path,
        strategy_info: Optional[EnabledStrategyInfo],
        task: AttributionTask,
        snapshot_sample: Optional[_SampleKey],
    ) -> CellExecuteResult:
        if task.cell.is_select:
            result = cls._lookup_selected_version(folder, task, snapshot_sample)
        else:
            result = cls._lookup_or_fill(folder, strategy_info, task)
        return cls._pin_ready(folder, result)

    @classmethod
    def _lookup_selected_version(
        cls,
        folder: Path,
        task: AttributionTask,
        snapshot_sample: Optional[_SampleKey],
    ) -> CellExecuteResult:
        vid = str(task.cell.version_id or "").strip()
        cached = SimulationVersionStore.get_cache_by_version_id(
            folder, vid, task.kind
        )
        if not cached:
            return CellExecuteResult(
                index=task.cell.index,
                status="skipped",
                version_id=vid or None,
                reason="version_not_found",
            )
        if snapshot_sample is not None:
            actual = cls._version_sample(folder, vid)
            if actual != snapshot_sample:
                logger.info(
                    "campaign sample mismatch: index=%s version=%s",
                    task.cell.index,
                    vid,
                )
                return CellExecuteResult(
                    index=task.cell.index,
                    status="skipped",
                    version_id=vid or None,
                    reason="sample_mismatch",
                )
        return cls._from_cache(task.cell.index, task.kind, cached)

    @classmethod
    def _lookup_or_fill(
        cls,
        folder: Path,
        strategy_info: Optional[EnabledStrategyInfo],
        task: AttributionTask,
    ) -> CellExecuteResult:
        if strategy_info is None:
            return CellExecuteResult(
                index=task.cell.index,
                status="skipped",
                reason="strategy_not_enabled",
            )
        fp_res = cls._fingerprints(strategy_info, task)
        cached = SimulationVersionStore.get_cache(folder, fp_res, task.kind)
        if cached:
            logger.info(
                "campaign cache hit: index=%s kind=%s version=%s",
                task.cell.index,
                task.kind.value,
                (cached.get(task.kind.value) or {}).get("version_id"),
            )
            return cls._from_cache(
                task.cell.index, task.kind, cached, fp_res=fp_res
            )
        if not task.fill_missing:
            logger.info(
                "campaign cache miss: index=%s kind=%s fill_missing=false",
                task.cell.index,
                task.kind.value,
            )
            return CellExecuteResult(
                index=task.cell.index,
                status="skipped",
                execute_fp=fp_res.execute_fp,
                env_fp=fp_res.env_fp,
                reason="fill_missing_false",
            )
        return cls._simulate_missing(strategy_info, task, fp_res)

    @classmethod
    def _simulate_missing(
        cls,
        strategy_info: EnabledStrategyInfo,
        task: AttributionTask,
        fp_res: FingerprintResult,
    ) -> CellExecuteResult:
        from core.modules.strategy.core.strategy import Strategy

        logger.info(
            "campaign fill_missing: index=%s kind=%s strategy=%s",
            task.cell.index,
            task.kind.value,
            strategy_info.key,
        )
        payload = Strategy.simulate(
            strategy_info.key,
            kind=task.kind,
            runtime_settings=task.cell.runtime_settings,
        )
        slot = payload.get(task.kind.value) if isinstance(payload, dict) else None
        slot_dict = slot if isinstance(slot, dict) else {}
        vid = str(payload.get("version_id") or slot_dict.get("version_id") or "").strip()
        output_dir = str(slot_dict.get("output_dir") or "").strip() or None
        return CellExecuteResult(
            index=task.cell.index,
            status="simulated",
            version_id=vid or None,
            execute_fp=fp_res.execute_fp,
            env_fp=fp_res.env_fp,
            output_dir=output_dir,
        )

    @classmethod
    def _fingerprints(
        cls,
        strategy_info: EnabledStrategyInfo,
        task: AttributionTask,
    ) -> FingerprintResult:
        runtime_settings = dict(task.cell.runtime_settings or {})
        stock_list = GlobalEntityCache.get_stock_list()
        merged, _diff = FingerprintCalculator.merge_settings(
            strategy_info, runtime_settings
        )
        usable = StrategySettings.to_usable(merged)
        entity_ids = SampleListResolver.resolve(
            strategy_info,
            usable,
            universe=stock_list,
        )
        return FingerprintCalculator.calculate_fingerprints(
            strategy_info,
            runtime_settings,
            entity_ids=entity_ids,
        )

    @classmethod
    def _from_cache(
        cls,
        index: int,
        kind: SimulateKind,
        cached: Dict[str, Any],
        *,
        fp_res: Optional[FingerprintResult] = None,
    ) -> CellExecuteResult:
        slot = cached.get(kind.value)
        slot_dict = slot if isinstance(slot, dict) else {}
        vid = str(slot_dict.get("version_id") or "").strip() or None
        output_dir = str(slot_dict.get("output_dir") or "").strip() or None
        return CellExecuteResult(
            index=index,
            status="hit",
            version_id=vid,
            execute_fp=fp_res.execute_fp if fp_res else None,
            env_fp=fp_res.env_fp if fp_res else None,
            output_dir=output_dir,
        )

    @classmethod
    def _pin_ready(
        cls,
        folder: Path,
        result: CellExecuteResult,
    ) -> CellExecuteResult:
        if result.status not in ("hit", "simulated"):
            return result
        vid = str(result.version_id or "").strip()
        if not vid:
            return result
        try:
            VersionMetaStore.set_version_pinned(
                ArtifactStore.simulations_root(folder),
                vid,
                True,
            )
            logger.info("campaign pin version=%s", vid)
        except FileNotFoundError:
            logger.warning("campaign pin skipped, version missing: %s", vid)
        except ValueError:
            logger.warning("campaign pin skipped, invalid version: %s", vid)
        return result

    @classmethod
    def _snapshot_sample(
        cls,
        folder: Path,
        strategy_info: Optional[EnabledStrategyInfo],
    ) -> Optional[_SampleKey]:
        if strategy_info is None:
            return None
        try:
            disk = load_settings_dict_from_folder(folder)
            usable = StrategySettings.to_usable(dict(disk))
            start, end = _resolved_dates(usable)
            entity_ids = SampleListResolver.resolve(
                strategy_info,
                usable,
                universe=GlobalEntityCache.get_stock_list(),
            )
            return (start, end, tuple(entity_ids))
        except Exception:
            logger.warning("campaign snapshot sample unavailable", exc_info=True)
            return None

    @classmethod
    def _version_sample(cls, folder: Path, version_id: str) -> Optional[_SampleKey]:
        scope = VersionMetaStore.read_scope(
            ArtifactStore.simulations_root(folder),
            version_id,
        )
        if not isinstance(scope, dict):
            return None
        ids = tuple(
            sorted(
                str(item).strip()
                for item in (scope.get("entity_ids") or [])
                if str(item).strip()
            )
        )
        return (
            str(scope.get("start_date") or "").strip(),
            str(scope.get("end_date") or "").strip(),
            ids,
        )

    @classmethod
    def _resolve_strategy_info(
        cls, folder: Path
    ) -> Optional[EnabledStrategyInfo]:
        disk = load_settings_dict_from_folder(folder)
        key = str((disk.get("meta") or {}).get("key") or "").strip()
        if key:
            found = DiscoveryService.find_strategy(key)
            if found is not None:
                return found
        target = Path(folder).resolve()
        for info in DiscoveryService.get_enabled_strategies():
            if info.resolved_folder().resolve() == target:
                return info
        return None


def _resolved_dates(usable: StrategySettings) -> Tuple[str, str]:
    start = str(usable.start_date or "").strip()
    end = str(usable.end_date or "").strip()
    try:
        period = usable.resolve_period()
        if getattr(period, "start_date", None):
            start = str(period.start_date).strip() or start
        if getattr(period, "end_date", None):
            end = str(period.end_date).strip() or end
    except Exception:
        pass
    return start, end
