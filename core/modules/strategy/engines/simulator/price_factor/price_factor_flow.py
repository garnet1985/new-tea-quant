#!/usr/bin/env python3
"""Price factor simulation flow."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

from core.modules.strategy.engines.simulator.base_flow import BaseSimulationFlow
from core.modules.strategy.services.data.output.enumerator_output_service import (
    EnumeratorOutputWriterService,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.flow_context import (
    PriceFactorExecuteContext,
    PriceFactorPreprocessContext,
)
from .price_factor_flow_impl import PriceFactorFlowImpl

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
        StrategySettingsView,
    )


def _stock_ids_for_db_cache_fingerprint(
    output_version_dir: Path,
    *,
    fallback_ids: List[str],
) -> List[str]:
    """
    DbCache env 中的 ``stock_ids`` 须与枚举 run 一致。

    优先读 ``0_scope_stock_ids.txt``（与 ``0_metadata.json`` 分列）；若无则读旧版元数据
    内嵌 ``fingerprint.stock_ids``；再不行则用 ``fallback_ids``（扫描到的成对 CSV）。
    """
    ids = EnumeratorOutputWriterService.read_scope_stock_ids(output_version_dir)
    if ids:
        return ids
    return sorted({str(s) for s in fallback_ids if s})


def _raw_settings_for_db_cache_fingerprint(
    base_settings: "StrategySettingsView",
    strategy_info: Optional["DiscoveredStrategy"],
) -> Dict[str, Any]:
    """
    与 ``EnumeratorRuntimeService.build_canonical_settings`` 同源：

    ``StrategyFingerprintManager.canonicalize_settings(strategy_info.settings)``，
    使 ``settings_fp`` / env 日期窗与 CLI 枚举路径对齐；不可用时回退 ``base_settings.to_dict()``。
    """
    if strategy_info is not None:
        try:
            from core.modules.strategy.services.runtime.run_service import (
                StrategyFingerprintManager,
            )

            return StrategyFingerprintManager.canonicalize_settings(
                dict(strategy_info.settings.to_dict())
            )
        except Exception:
            pass
    return dict(base_settings.to_dict())


class _PriceFactorProbe(NamedTuple):
    """枚举输出解析完成后、尚未创建本次 price_factor 版本目录前的中间状态。"""

    strategy_name: str
    base_settings: "StrategySettingsView"
    simulator_config: Any
    output_version_dir: Path
    output_root: Path
    stock_files: Dict[str, Dict[str, Path]]


class PriceFactorFlow(BaseSimulationFlow):
    """Three-stage price factor simulation flow（支持 Simulator Res DB Cache）。"""

    def __init__(self, is_verbose: bool = False, *, force_refresh: bool = False) -> None:
        self._impl = PriceFactorFlowImpl(is_verbose=is_verbose)
        self._force_refresh = bool(force_refresh)
        self.last_snapshot_id: int = 0
        self.last_run_used_db_cache: bool = False

    def _probe(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> _PriceFactorProbe:
        base_settings = self._impl.load_settings(strategy_name, strategy_info)
        simulator_config = self._impl.parse_config(base_settings)
        output_version_dir, output_root = self._impl.resolve_source_version(
            strategy_name=strategy_name,
            base_settings=base_settings,
            config=simulator_config,
            strategy_info=strategy_info,
        )
        stock_files = self._impl.scan_stock_files(output_version_dir)
        return _PriceFactorProbe(
            strategy_name=strategy_name,
            base_settings=base_settings,
            simulator_config=simulator_config,
            output_version_dir=output_version_dir,
            output_root=output_root,
            stock_files=stock_files,
        )

    def _finish_probe(self, probe: _PriceFactorProbe) -> PriceFactorPreprocessContext:
        sim_version_dir, sim_version_id = self._impl.create_simulation_version(
            probe.strategy_name
        )
        return PriceFactorPreprocessContext(
            strategy_name=probe.strategy_name,
            base_settings=probe.base_settings,
            simulator_config=probe.simulator_config,
            output_version_dir=probe.output_version_dir,
            output_root=probe.output_root,
            sim_version_dir=sim_version_dir,
            sim_version_id=sim_version_id,
            stock_files=probe.stock_files,
        )

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
    ) -> Any:
        """
        轻量 probe → 指纹解析成功则尝试 DbCache → 否则创建版本目录并
        preprocess（等价）→ execute → postprocess → 再写缓存。
        """
        from core.modules.data_manager import DataManager
        from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
            lookup_price_factor_cache,
            persist_price_factor_snapshot,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
            resolve_db_cache_fingerprints,
        )

        self.last_snapshot_id = 0
        self.last_run_used_db_cache = False

        probe = self._probe(strategy_name=strategy_name, strategy_info=strategy_info)
        stock_list = _stock_ids_for_db_cache_fingerprint(
            probe.output_version_dir,
            fallback_ids=sorted(probe.stock_files.keys()),
        )
        raw_for_fp = _raw_settings_for_db_cache_fingerprint(
            probe.base_settings, strategy_info
        )

        data_mgr = DataManager(is_verbose=False)
        latest_completed_trading_date = str(
            data_mgr.service.calendar.get_latest_completed_trading_date() or ""
        ).strip()

        resolved_probe = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            raw_settings=raw_for_fp,
            stock_list=list(stock_list),
            latest_completed_trading_date=latest_completed_trading_date,
        )

        if resolved_probe is not None and not self._force_refresh:
            hit = lookup_price_factor_cache(
                strategy_name,
                resolved_probe.settings_fp,
                resolved_probe.env_fp,
            )
            if hit:
                summary, snapshot_id = hit
                self.last_snapshot_id = int(snapshot_id or 0)
                self.last_run_used_db_cache = True
                return summary

        preprocessed = self._finish_probe(probe)
        executed = self.execute(preprocessed)
        summary = self.postprocess(preprocessed, executed)

        if summary and isinstance(summary, dict):
            raw_save = _raw_settings_for_db_cache_fingerprint(
                preprocessed.base_settings, strategy_info
            )
            resolved_save = resolve_db_cache_fingerprints(
                strategy_name=str(strategy_name),
                raw_settings=raw_save,
                stock_list=list(stock_list),
                latest_completed_trading_date=latest_completed_trading_date,
            )
            if resolved_save is not None:
                sid = persist_price_factor_snapshot(
                    strategy_name,
                    settings_snapshot_api=dict(resolved_save.normalized_settings_dict or {}),
                    report_price_factor=summary,
                    settings_fingerprint_id=resolved_save.settings_fp,
                    env_fingerprint_id=resolved_save.env_fp,
                )
                self.last_snapshot_id = int(sid or 0)
        return summary

    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> PriceFactorPreprocessContext:
        probe = self._probe(strategy_name=strategy_name, strategy_info=strategy_info)
        return self._finish_probe(probe)

    def execute(self, preprocessed: PriceFactorPreprocessContext) -> PriceFactorExecuteContext:
        jobs = self._impl.build_worker_jobs(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            stock_files=preprocessed.stock_files,
            config=preprocessed.simulator_config,
        )
        results = self._impl.run_worker_jobs(
            jobs=jobs, max_workers=preprocessed.simulator_config.max_workers
        )
        collected = self._impl.collect_stock_summaries(results)
        return PriceFactorExecuteContext(
            stock_summaries=collected["stock_summaries"],
            aggregate_profiler=collected["aggregate_profiler"],
        )

    def postprocess(
        self,
        preprocessed: PriceFactorPreprocessContext,
        executed: PriceFactorExecuteContext,
    ) -> Dict[str, object]:
        session_summary = self._impl.build_session_summary(
            stock_summaries=executed.stock_summaries,
            output_version_dir=preprocessed.output_version_dir,
            output_root=preprocessed.output_root,
            sim_version_dir=preprocessed.sim_version_dir,
            sim_version_id=preprocessed.sim_version_id,
        )
        if not session_summary:
            return {}
        self._impl.save_session_outputs(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            sim_version_id=preprocessed.sim_version_id,
            output_version_dir=preprocessed.output_version_dir,
            session_summary=session_summary,
            settings_snapshot=preprocessed.base_settings.to_dict(),
        )
        self._impl.save_performance_report(
            sim_version_dir=preprocessed.sim_version_dir,
            aggregate_profiler=executed.aggregate_profiler,
        )
        self._impl.run_analyzer_hook(
            strategy_name=preprocessed.strategy_name,
            sim_version_dir=preprocessed.sim_version_dir,
            raw_settings=preprocessed.base_settings.to_dict(),
        )
        return session_summary


__all__ = ["PriceFactorFlow"]
