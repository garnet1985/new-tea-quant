"""每格 ``Strategy.simulate``；命中/补跑由回测层判断。

归因只写主号下的副本 ``{vid}-{r}``；baseline 复用主号。
任务 ``steps`` 含到本层为止的上游链（见 ``simulate_steps_for_kind``）：
``sea`` 只枚举，``spa`` 枚举→价格，``soa`` 枚举→价格→组合；已有产物则 cache hit。
``ignore_cache`` 只加在该格第一层，避免 -f 把后面刚写下的下游清掉。
选号按 version_id 取已有主号产物，不补层。
"""
from __future__ import annotations

import logging
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    ArtifactRetention,
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
from core.modules.strategy.core.services.progress import (
    ATTRIBUTE_PIPELINE,
    PipelineProgress,
)

from ..plan import AttributionCell, AttributionTask, cell_identity
from .models import CellExecuteResult

logger = logging.getLogger(__name__)

_SampleKey = Tuple[str, str, Tuple[str, ...]]


class ExecuteBase:
    """战役执行基类：inputs 展格 / 滚动交给 simulate；选号只读已有 version。

    格子按 ``cell_identity`` 去重后再 simulate；
    各家族再用 ``bind`` 领回自己的行。
    """

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    @classmethod
    def unique_tasks(
        cls, tasks: Sequence[AttributionTask]
    ) -> List[AttributionTask]:
        seen: Dict[str, int] = {}
        unique: List[AttributionTask] = []
        next_index = 0
        for task in tasks:
            key = cell_identity(task.cell)
            if key in seen:
                continue
            cell = replace(task.cell, index=next_index)
            unique.append(
                AttributionTask(cell=cell, kind=task.kind, steps=task.steps)
            )
            seen[key] = next_index
            next_index += 1
        return unique

    @classmethod
    def bind(
        cls,
        executed: Mapping[str, Any],
        unique_cells: Sequence[AttributionCell],
        family_cells: Sequence[AttributionCell],
    ) -> Dict[str, Any]:
        by_key: Dict[str, Dict[str, Any]] = {}
        raws = [
            row for row in executed.get("cells") or [] if isinstance(row, dict)
        ]
        for cell, raw in zip(unique_cells, raws):
            by_key[cell_identity(cell)] = raw
        out_cells: List[Dict[str, Any]] = []
        hits: List[int] = []
        simulated: List[int] = []
        skipped: List[int] = []
        for cell in family_cells:
            raw = by_key.get(cell_identity(cell))
            if raw is None:
                out_cells.append(
                    {
                        "index": cell.index,
                        "status": "skipped",
                        "reason": "execute_identity_missing",
                    }
                )
                skipped.append(cell.index)
                continue
            copied = dict(raw)
            copied["index"] = cell.index
            out_cells.append(copied)
            status = str(copied.get("status") or "")
            if status == "hit":
                hits.append(cell.index)
            elif status == "simulated":
                simulated.append(cell.index)
            else:
                skipped.append(cell.index)
        out = dict(executed)
        out["task_count"] = len(family_cells)
        out["hits"] = hits
        out["simulated"] = simulated
        out["skipped"] = skipped
        out["misses"] = skipped
        out["cells"] = out_cells
        return out

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        *,
        kind: Optional[SimulateKind] = None,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        layer = kind if isinstance(kind, SimulateKind) else cls.KIND
        strategy_info = cls._resolve_strategy_info(folder)
        if strategy_info is None:
            raise ValueError(f"当前策略不存在或未启用: {folder}")
        baseline_fp = cls._baseline_fingerprints(strategy_info)
        root = ArtifactStore.simulations_root(folder)
        parent_vid = VersionMetaStore.require_primary_version(
            root,
            baseline_fp.execute_fp,
            baseline_fp.env_fp,
            kind=layer,
        )
        snapshot_sample = None
        if any(task.cell.is_select for task in tasks):
            snapshot_sample = cls._snapshot_sample(folder, strategy_info)
        drive = PipelineProgress.drives_pipeline(ATTRIBUTE_PIPELINE)
        total = len(tasks)
        rows: List[CellExecuteResult] = []
        for idx, task in enumerate(tasks, start=1):
            rows.append(
                cls._run_one(
                    folder,
                    strategy_info,
                    task,
                    snapshot_sample,
                    parent_version_id=parent_vid,
                    baseline_execute_fp=str(baseline_fp.execute_fp or ""),
                    ignore_cache=ignore_cache,
                )
            )
            if drive:
                PipelineProgress.tick_execute_bound(idx, total)
        hits = [row.index for row in rows if row.status == "hit"]
        simulated = [row.index for row in rows if row.status == "simulated"]
        skipped = [row.index for row in rows if row.status == "skipped"]
        cls._prune_stale_envs(folder, strategy_info)
        return {
            "status": "ok",
            "folder": str(Path(folder).resolve()),
            "ignore_cache": ignore_cache,
            "parent_version_id": parent_vid,
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
        *,
        parent_version_id: str,
        baseline_execute_fp: str,
        ignore_cache: bool,
    ) -> CellExecuteResult:
        if task.cell.is_select:
            return cls._lookup_selected_version(folder, task, snapshot_sample)
        return cls._simulate(
            folder,
            strategy_info,
            task,
            parent_version_id=parent_version_id,
            baseline_execute_fp=baseline_execute_fp,
            ignore_cache=ignore_cache,
        )

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
    def _simulate(
        cls,
        folder: Path,
        strategy_info: Optional[EnabledStrategyInfo],
        task: AttributionTask,
        *,
        parent_version_id: str,
        baseline_execute_fp: str,
        ignore_cache: bool,
    ) -> CellExecuteResult:
        if strategy_info is None:
            return CellExecuteResult(
                index=task.cell.index,
                status="skipped",
                reason="strategy_not_enabled",
            )
        if task.cell.family == "allocation":
            return cls._simulate_allocation(
                folder,
                strategy_info,
                task,
                parent_version_id=parent_version_id,
                baseline_execute_fp=baseline_execute_fp,
                ignore_cache=ignore_cache,
            )
        fp_res = cls._fingerprints(strategy_info, task)
        from core.modules.strategy.core.strategy import Strategy

        root = ArtifactStore.simulations_root(folder)
        if str(fp_res.execute_fp or "") == str(baseline_execute_fp or ""):
            target_vid = str(parent_version_id)
        else:
            target_vid = VersionMetaStore.allocate_replica_id(
                root,
                parent_version_id,
                execute_fp=str(fp_res.execute_fp or ""),
                env_fp=str(fp_res.env_fp or ""),
            )

        steps = tuple(task.steps) or (task.kind,)
        payload: Any = None
        any_miss = False
        for i, sim_kind in enumerate(steps):
            force = bool(ignore_cache) and i == 0
            logger.info(
                "campaign simulate: index=%s kind=%s strategy=%s version=%s ignore_cache=%s",
                task.cell.index,
                sim_kind.value,
                strategy_info.key,
                target_vid,
                force,
            )
            payload = Strategy.simulate(
                strategy_info.key,
                kind=sim_kind,
                ignore_cache=force,
                runtime_settings=task.cell.runtime_settings,
                version_id=target_vid,
            )
            if not (isinstance(payload, dict) and payload.get("cache_hit")):
                any_miss = True
        last_kind = steps[-1]
        slot = payload.get(last_kind.value) if isinstance(payload, dict) else None
        slot_dict = slot if isinstance(slot, dict) else {}
        vid = ""
        if isinstance(payload, dict):
            vid = str(
                payload.get("version_id") or slot_dict.get("version_id") or target_vid or ""
            ).strip()
        output_dir = str(slot_dict.get("output_dir") or "").strip() or None
        return CellExecuteResult(
            index=task.cell.index,
            status="simulated" if any_miss else "hit",
            version_id=vid or target_vid,
            execute_fp=fp_res.execute_fp,
            env_fp=fp_res.env_fp,
            output_dir=output_dir,
        )

    @classmethod
    def _simulate_allocation(
        cls,
        folder: Path,
        strategy_info: Optional[EnabledStrategyInfo],
        task: AttributionTask,
        *,
        parent_version_id: str,
        baseline_execute_fp: str,
        ignore_cache: bool,
    ) -> CellExecuteResult:
        """只重跑组合。枚举产物用主 version，不按新指纹重算枚举和价格。"""
        if strategy_info is None:
            return CellExecuteResult(
                index=task.cell.index,
                status="skipped",
                reason="strategy_not_enabled",
            )
        fp_res = cls._fingerprints(strategy_info, task)
        from core.modules.strategy.core.strategy import Strategy

        parent = str(parent_version_id or "").strip()
        if str(fp_res.execute_fp or "") == str(baseline_execute_fp or ""):
            target_vid = parent
        else:
            root = ArtifactStore.simulations_root(folder)
            target_vid = VersionMetaStore.allocate_replica_id(
                root,
                parent,
                execute_fp=str(fp_res.execute_fp or ""),
                env_fp=str(fp_res.env_fp or ""),
            )
        logger.info(
            "allocation simulate: index=%s strategy=%s version=%s upstream=%s",
            task.cell.index,
            strategy_info.key,
            target_vid,
            parent,
        )
        payload = Strategy.simulate(
            strategy_info.key,
            kind=SimulateKind.PORTFOLIO,
            ignore_cache=ignore_cache,
            runtime_settings=task.cell.runtime_settings,
            version_id=target_vid,
            upstream_version_id=parent,
        )
        slot = payload.get(SimulateKind.PORTFOLIO.value) if isinstance(payload, dict) else None
        slot_dict = slot if isinstance(slot, dict) else {}
        vid = ""
        if isinstance(payload, dict):
            vid = str(
                payload.get("version_id") or slot_dict.get("version_id") or target_vid or ""
            ).strip()
        output_dir = str(slot_dict.get("output_dir") or "").strip() or None
        hit = bool(isinstance(payload, dict) and payload.get("cache_hit"))
        return CellExecuteResult(
            index=task.cell.index,
            status="hit" if hit else "simulated",
            version_id=vid or target_vid,
            execute_fp=fp_res.execute_fp,
            env_fp=fp_res.env_fp,
            output_dir=output_dir,
        )

    @classmethod
    def _baseline_fingerprints(
        cls, strategy_info: EnabledStrategyInfo
    ) -> FingerprintResult:
        stock_list = GlobalEntityCache.get_stock_list()
        usable = StrategySettings.to_usable(
            FingerprintCalculator.merge_settings(strategy_info, None)[0]
        )
        entity_ids = SampleListResolver.resolve(
            strategy_info,
            usable,
            universe=stock_list,
        )
        return FingerprintCalculator.calculate_fingerprints(
            strategy_info,
            None,
            entity_ids=entity_ids,
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
    def _prune_stale_envs(
        cls,
        folder: Path,
        strategy_info: Optional[EnabledStrategyInfo],
    ) -> None:
        if strategy_info is None:
            return
        env_fp = str(FingerprintCalculator.to_env_fingerprint(strategy_info) or "")
        if not env_fp:
            return
        try:
            ArtifactRetention.prune_simulation_results(str(folder), env_fp=env_fp)
        except Exception:
            logger.exception("campaign prune stale envs failed")

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
