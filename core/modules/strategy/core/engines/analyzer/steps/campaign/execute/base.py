"""按格调用模拟。副本写在主版本下，基准格复用主版本。"""
from __future__ import annotations

import json
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


def _without_price_replay(settings: Mapping[str, Any]) -> Dict[str, Any]:
    """去掉 ``simulation.price``，留下决定枚举结果的 settings。"""
    out = dict(settings)
    simulation = out.get("simulation")
    if not isinstance(simulation, dict) or "price" not in simulation:
        return out
    simulation = dict(simulation)
    simulation.pop("price", None)
    if simulation:
        out["simulation"] = simulation
    else:
        out.pop("simulation", None)
    return out


def _canonical_settings(settings: Mapping[str, Any]) -> str:
    return json.dumps(settings, sort_keys=True, default=str, ensure_ascii=False)


def _prefer_version_id(version_ids: Sequence[str]) -> str:
    """主号优先于副本，同级取编号较小的。"""
    if not version_ids:
        return ""

    def sort_key(vid: str) -> Tuple[int, int, str]:
        parent, _, rest = str(vid).partition("-")
        parent_n = int(parent) if parent.isdigit() else 10**9
        replica_n = int(rest) if rest.isdigit() else -1
        return (parent_n, replica_n, vid)

    return sorted(version_ids, key=sort_key)[0]


class ExecuteBase:
    """执行战役格子。相同执行身份先去重，各家族再领回自己的行。"""

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    @classmethod
    def unique_tasks(
        cls, tasks: Sequence[AttributionTask]
    ) -> List[AttributionTask]:
        """按执行身份去掉重复任务。"""
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
        """把去重后的结果领回各家族的行。"""
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
        """模拟本层格子。"""
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
        drive = PipelineProgress.drives_pipeline(ATTRIBUTE_PIPELINE)
        total = len(tasks)
        rows: List[CellExecuteResult] = []
        for idx, task in enumerate(tasks, start=1):
            rows.append(
                cls._run_one(
                    folder,
                    strategy_info,
                    task,
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
        *,
        parent_version_id: str,
        baseline_execute_fp: str,
        ignore_cache: bool,
    ) -> CellExecuteResult:
        return cls._simulate(
            folder,
            strategy_info,
            task,
            parent_version_id=parent_version_id,
            baseline_execute_fp=baseline_execute_fp,
            ignore_cache=ignore_cache,
        )

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
        if task.kind == SimulateKind.PRICE_FACTOR:
            upstream = cls._reusable_enum_version(
                folder,
                task,
                parent_version_id=parent_version_id,
            )
            if upstream:
                return cls._simulate_downstream(
                    folder,
                    strategy_info,
                    task,
                    kind=SimulateKind.PRICE_FACTOR,
                    upstream_version_id=upstream,
                    parent_version_id=parent_version_id,
                    baseline_execute_fp=baseline_execute_fp,
                    ignore_cache=ignore_cache,
                )
        if task.cell.family == "allocation":
            return cls._simulate_downstream(
                folder,
                strategy_info,
                task,
                kind=SimulateKind.PORTFOLIO,
                upstream_version_id=parent_version_id,
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
    def _reusable_enum_version(
        cls,
        folder: Path,
        task: AttributionTask,
        *,
        parent_version_id: str,
    ) -> str:
        """已有枚举与本格去掉 ``simulation.price`` 后相同，则复用该版本。"""
        cell_settings = task.cell.execute_settings
        if not isinstance(cell_settings, dict) or not cell_settings:
            return ""
        root = ArtifactStore.simulations_root(folder)
        try:
            meta = VersionMetaStore.read_root_meta(root)
        except Exception:
            return ""
        registry = meta.get("registry") if isinstance(meta, dict) else None
        if not isinstance(registry, dict):
            return ""
        parent = str(parent_version_id or "").strip()
        target = _canonical_settings(_without_price_replay(cell_settings))
        exact_target = _canonical_settings(cell_settings)
        exact: List[str] = []
        identity: List[str] = []
        for raw_vid, entry in registry.items():
            vid = str(raw_vid or "").strip()
            if not vid or not isinstance(entry, dict):
                continue
            if parent and vid != parent and not vid.startswith(f"{parent}-"):
                continue
            if VersionMetaStore.step_status(root, vid, SimulateKind.ENUMERATE) != "ok":
                continue
            stored = VersionMetaStore.read_effective_settings(root, vid)
            if not isinstance(stored, dict) or not stored:
                continue
            if _canonical_settings(stored) == exact_target:
                exact.append(vid)
            elif _canonical_settings(_without_price_replay(stored)) == target:
                identity.append(vid)
        chosen = _prefer_version_id(exact or identity)
        return chosen

    @classmethod
    def _simulate_downstream(
        cls,
        folder: Path,
        strategy_info: Optional[EnabledStrategyInfo],
        task: AttributionTask,
        *,
        kind: SimulateKind,
        upstream_version_id: str,
        parent_version_id: str,
        baseline_execute_fp: str,
        ignore_cache: bool,
    ) -> CellExecuteResult:
        """沿已有上游重跑本层。指纹没变就写回主版本，变了才开副本。"""
        if strategy_info is None:
            return CellExecuteResult(
                index=task.cell.index,
                status="skipped",
                reason="strategy_not_enabled",
            )
        fp_res = cls._fingerprints(strategy_info, task)
        from core.modules.strategy.core.strategy import Strategy

        parent = str(parent_version_id or "").strip()
        upstream = str(upstream_version_id or "").strip()
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
            "%s simulate: index=%s strategy=%s version=%s upstream=%s",
            kind.value,
            task.cell.index,
            strategy_info.key,
            target_vid,
            upstream,
        )
        payload = Strategy.simulate(
            strategy_info.key,
            kind=kind,
            ignore_cache=ignore_cache,
            runtime_settings=task.cell.runtime_settings,
            version_id=target_vid,
            upstream_version_id=upstream,
        )
        slot = payload.get(kind.value) if isinstance(payload, dict) else None
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

