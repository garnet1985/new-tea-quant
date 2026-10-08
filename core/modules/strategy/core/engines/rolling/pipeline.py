"""滚动对照编排：三层回测齐全且写了 rolling.py 才跑。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from core.modules.strategy.core.engines.rolling.config import load_rolling_windows
from core.modules.strategy.core.engines.rolling.report import (
    assemble_report,
    compare_window,
    load_version_metrics,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
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

logger = logging.getLogger(__name__)

_REQUIRED = (
    SimulateKind.ENUMERATE,
    SimulateKind.PRICE_FACTOR,
    SimulateKind.PORTFOLIO,
)
_LAYER_LABEL = {
    SimulateKind.ENUMERATE: "枚举",
    SimulateKind.PRICE_FACTOR: "价格",
    SimulateKind.PORTFOLIO: "资金",
}


class RollingPipeline:
    """同一套设置，按 rolling.py 的窗口再模拟，写出一份对照报告。"""

    @classmethod
    def run(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """窗口跑完后，把报告写到主 version 的 ``rolling/report.json``。"""
        strategy_info = DiscoveryService.find_strategy(str(key_or_id))
        if strategy_info is None:
            raise ValueError(f"当前策略不存在或未启用: {key_or_id}")
        folder = DiscoveryService.resolve_strategy_folder(str(key_or_id))
        windows = load_rolling_windows(folder, strategy_key=strategy_info.key)
        baseline_fp = _fingerprints(strategy_info, None)
        root = ArtifactStore.simulations_root(folder)
        parent = _require_finished_primary(root, baseline_fp)
        baseline_start, baseline_end = _baseline_period(root, parent, strategy_info)
        baseline_metrics = load_version_metrics(folder, parent)

        rows: List[Dict[str, Any]] = []
        for window in windows:
            version_id = cls._run_window(
                strategy_info,
                root,
                parent,
                baseline_fp,
                window,
                ignore_cache=ignore_cache,
            )
            rows.append(
                compare_window(
                    baseline_metrics,
                    load_version_metrics(folder, version_id),
                    version_id=version_id,
                    start=window["start"],
                    end=window["end"],
                    baseline_start=baseline_start,
                    baseline_end=baseline_end,
                )
            )

        report = assemble_report(
            parent_version_id=parent,
            baseline_start=baseline_start,
            baseline_end=baseline_end,
            baseline_metrics=baseline_metrics,
            windows=rows,
        )
        report_path = _write_report(root, parent, report)
        report["success"] = True
        report["folder"] = str(folder.resolve())
        report["report_path"] = str(report_path.resolve())
        report["ignore_cache"] = ignore_cache
        return report

    @classmethod
    def _run_window(
        cls,
        strategy_info: EnabledStrategyInfo,
        root: Path,
        parent: str,
        baseline_fp: FingerprintResult,
        window: Dict[str, str],
        *,
        ignore_cache: bool,
    ) -> str:
        from core.modules.strategy.core.strategy import Strategy

        strategy_key = str(strategy_info.key)
        runtime = {
            "simulation": {
                "execution": {
                    "start_date": window["start"],
                    "end_date": window["end"],
                }
            }
        }
        fp_res = _fingerprints(strategy_info, runtime)
        if (
            str(fp_res.execute_fp or "") == str(baseline_fp.execute_fp or "")
            and str(fp_res.env_fp or "") == str(baseline_fp.env_fp or "")
        ):
            return parent
        version_id = VersionMetaStore.allocate_rolling_id(
            root,
            parent,
            execute_fp=str(fp_res.execute_fp or ""),
            env_fp=str(fp_res.env_fp or ""),
        )
        logger.info(
            "rolling window %s %s-%s ignore_cache=%s",
            version_id,
            window["start"],
            window["end"],
            ignore_cache,
        )
        Strategy.simulate(
            strategy_key,
            kind=SimulateKind.ENUMERATE,
            ignore_cache=ignore_cache,
            runtime_settings=runtime,
            version_id=version_id,
        )
        for kind in (SimulateKind.PRICE_FACTOR, SimulateKind.PORTFOLIO):
            Strategy.simulate(
                strategy_key,
                kind=kind,
                ignore_cache=ignore_cache,
                runtime_settings=runtime,
                version_id=version_id,
                upstream_version_id=version_id,
            )
        missing = _missing_steps(root, version_id)
        if missing:
            names = "、".join(_LAYER_LABEL[kind] for kind in missing)
            raise ValueError(f"滚动窗口 {version_id} 没有完成{names}。")
        return version_id


def _require_finished_primary(root: Path, fp_res: FingerprintResult) -> str:
    parent = VersionMetaStore.find_version_by_fingerprints(
        root,
        str(fp_res.execute_fp or ""),
        str(fp_res.env_fp or ""),
    )
    if not parent:
        raise ValueError(
            "滚动对照需要当前 settings 已经完成枚举、价格和资金回测。"
            "请先跑完这三步。"
        )
    missing = _missing_steps(root, parent)
    if missing:
        names = "、".join(_LAYER_LABEL[kind] for kind in missing)
        raise ValueError(
            f"主 version {parent} 还没有{names}产物。"
            "滚动对照需要枚举、价格和资金回测都完成。"
        )
    return parent


def _missing_steps(root: Path, version_id: str) -> Tuple[SimulateKind, ...]:
    return tuple(
        kind
        for kind in _REQUIRED
        if VersionMetaStore.step_status(root, version_id, kind) != "ok"
    )


def _baseline_period(
    root: Path,
    parent: str,
    strategy_info: EnabledStrategyInfo,
) -> Tuple[str, str]:
    scope = VersionMetaStore.read_scope(root, parent) or {}
    start = str(scope.get("start_date") or "").strip()
    end = str(scope.get("end_date") or "").strip()
    if start and end:
        return start, end
    usable = StrategySettings.to_usable(dict(strategy_info.settings or {}))
    return usable.start_date, usable.end_date


def _fingerprints(
    strategy_info: EnabledStrategyInfo,
    runtime_settings: Optional[Dict[str, Any]],
) -> FingerprintResult:
    stock_list = GlobalEntityCache.get_stock_list()
    merged, _diff = FingerprintCalculator.merge_settings(strategy_info, runtime_settings)
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


def _write_report(root: Path, parent: str, report: Dict[str, Any]) -> Path:
    path = root / parent / "rolling" / "report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
