"""工作台规划用指纹探针（仅解析已有枚举目录，不触发 ``resolve_or_build``）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )

__all__ = [
    "enum_db_cache_aligned_with_downstream_probe",
]


def _latest_trading_date_for_db_cache() -> str:
    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=False)
    return str(
        data_mgr.stock.kline.load_latest_date("daily")
        or data_mgr.service.calendar.get_latest_completed_trading_date()
        or ""
    ).strip()


def _try_resolve_existing_enumerator_dir(
    strategy_name: str,
    *,
    use_sampling: bool,
    base_version: str,
):
    """仅解析已有枚举输出目录；缺失时 ``None``。"""
    from core.modules.strategy.services.data.output import StrategyOutputVersionService

    _ = use_sampling  # stock universe only; enum artifacts share one root
    raw_version = (str(base_version or "latest")).strip()
    if "/" in raw_version:
        raw_version = raw_version.split("/", 1)[1].strip() or "latest"
    version_spec = raw_version
    name = str(strategy_name).strip()
    for spec in (version_spec, "latest"):
        try:
            version_dir, _parent = StrategyOutputVersionService.resolve_enumerator_version(
                name, spec
            )
            return version_dir
        except FileNotFoundError:
            continue
    return None


def _fingerprint_resolution_using_existing_enum_dir(
    norm_step: str,
    strategy_name: str,
    discovered: "DiscoveredStrategy",
):
    """
    与 ``PriceFactorFlow.run`` / ``CapitalAllocationFlow.run`` 的指纹入参一致，但枚举目录仅做
    ``StrategyOutputVersionService.resolve_enumerator_version``。
    """
    from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow_impl import (
        CapitalAllocationFlowImpl,
    )
    from core.modules.strategy.engines.simulator.price_factor.price_factor_flow_impl import (
        PriceFactorFlowImpl,
    )
    from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.finger_print import (
        resolve_db_cache_fingerprints,
    )
    from core.modules.strategy.services.cache.simulator_res_db_cache.helpers import (
        raw_settings_for_db_cache_fingerprint,
        stock_ids_for_db_cache_fingerprint,
    )

    name = str(strategy_name).strip()
    if norm_step == "price":
        impl = PriceFactorFlowImpl(is_verbose=False)
        base_settings = impl.load_settings(name, discovered)
        config = impl.parse_config(base_settings)
    elif norm_step == "capital":
        impl = CapitalAllocationFlowImpl(is_verbose=False)
        base_settings = impl.load_settings(name, discovered)
        config = impl.parse_config(base_settings)
    else:
        return None

    ev_dir = _try_resolve_existing_enumerator_dir(
        name,
        use_sampling=config.use_sampling,
        base_version=config.base_version,
    )
    if ev_dir is None:
        return None

    scan = PriceFactorFlowImpl(is_verbose=False).scan_stock_files(ev_dir)
    stock_list = stock_ids_for_db_cache_fingerprint(
        ev_dir,
        fallback_ids=sorted(scan.keys()),
    )
    raw_for_fp = raw_settings_for_db_cache_fingerprint(base_settings, discovered)
    return resolve_db_cache_fingerprints(
        strategy_name=name,
        raw_settings=raw_for_fp,
        stock_list=list(stock_list),
        latest_completed_trading_date=_latest_trading_date_for_db_cache(),
    )


def enum_db_cache_aligned_with_downstream_probe(
    strategy_name: str,
    norm_step: str,
    discovered: "DiscoveredStrategy",
) -> bool:
    """下游 price / capital 与枚举 DbCache 双指纹一致且表中有非空 ``enum`` 槽位。"""
    from core.modules.strategy.services.cache.simulator_res_db_cache.snapshot_slot_adapters import (
        lookup_enum_cache,
    )

    name = str(strategy_name).strip()
    resolved = _fingerprint_resolution_using_existing_enum_dir(
        norm_step, name, discovered
    )
    if resolved is None:
        return False
    return (
        lookup_enum_cache(name, resolved.settings_fp, resolved.env_fp) is not None
    )
