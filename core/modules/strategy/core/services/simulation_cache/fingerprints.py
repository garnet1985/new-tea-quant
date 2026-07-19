"""模拟指纹服务：settings_fp / env_fp 解析与哈希（进入引擎前）。"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.system import get_version


@dataclass(frozen=True)
class FingerprintResult:
    """一次模拟请求的共享指纹与有效 settings。

    边界:
    - 负责: 供编排层查缓存、供各 Pipeline 使用
    - 不负责: 缓存读写本身
    """

    global_entity_cache: GlobalEntityCache
    settings_fp: str
    env_fp: str
    settings_diff: Dict[str, Any]
    effective_settings: StrategySettings
    entity_ids: List[str]


class FingerprintCalculator:
    """指纹计算入口：effective settings、GlobalEntityCache seed、settings_fp / env_fp。"""

    @staticmethod
    def calculate_fingerprints(
        strategy_info: EnabledStrategyInfo,
        runtime_settings: Optional[Dict[str, Any]] = None,
        stock_list: Optional[List[str]] = None,
        latest_completed_trading_date: Optional[str] = None,
    ) -> FingerprintResult:
        """计算指纹；stock_list / latest_date 由编排层预取时不再重复加载。"""
        if strategy_info is None:
            raise ValueError("strategy_info 不能为空")

        effective_settings, settings_diff = StrategySettings.calculate_effective_settings(
            disk_settings=strategy_info.settings,
            user_settings=runtime_settings or {},
        )
        cache = GlobalEntityCache(effective_settings)
        cache.seed_system_globals(
            stock_list=stock_list,
            latest_completed_trading_date=latest_completed_trading_date,
        )
        cache.init_trade_calendar()

        entity_ids = list(cache.get_stock_ids())
        settings_fp = FingerprintCalculator.to_settings_diff_fingerprint(
            settings_diff, entity_ids
        )
        env_fp = FingerprintCalculator.to_env_fingerprint(
            strategy_info,
            effective_settings,
            entity_ids=entity_ids,
        )
        return FingerprintResult(
            global_entity_cache=cache,
            settings_fp=settings_fp,
            env_fp=env_fp,
            settings_diff=settings_diff,
            effective_settings=effective_settings,
            entity_ids=entity_ids,
        )

    @staticmethod
    def to_settings_diff_fingerprint(
        settings_diff: Dict[str, Any],
        entity_ids: List[str],
    ) -> str:
        """settings 指纹：settings_diff + entity_ids。"""
        signature = {
            "settings_diff": settings_diff,
            "entity_ids": sorted(entity_ids),
        }
        return FingerprintCalculator._to_fingerprint_hash(signature)

    @staticmethod
    def to_env_fingerprint(
        strategy_info: EnabledStrategyInfo,
        effective_settings: Union[StrategySettings, Dict[str, Any]],
        *,
        entity_ids: List[str],
        hooks_file_path: str = "",
    ) -> str:
        """env 指纹：策略代码 / 区间 / execution_mode / 引擎与 DB / data_contract mapping。"""
        if isinstance(effective_settings, StrategySettings):
            raw_settings = effective_settings.raw_settings
        else:
            raw_settings = dict(effective_settings or {})

        simulation = raw_settings.get("simulation") or {}
        start_date = simulation.get("start_date", "")
        end_date = simulation.get("end_date", "")

        path = hooks_file_path or str(getattr(strategy_info, "strategy_file", "") or "")
        hooks_class = getattr(strategy_info, "hooks_class", None)
        hooks_class_name = hooks_class.__name__ if hooks_class is not None else ""

        signature = {
            "strategy_id": getattr(strategy_info, "unique_relative_path", "") or "",
            "entity_ids": sorted(entity_ids or []),
            "start_date": start_date,
            "end_date": end_date,
            "execution_mode": raw_settings.get("execution_mode", "entity_timeline"),
            "engine_version": get_version(),
            "database_type": FingerprintCalculator._get_database_type(),
            "hooks_module_path": getattr(strategy_info, "hooks_module_path", "") or "",
            "hooks_class_name": hooks_class_name,
            "hooks_code_hash": FingerprintCalculator._hash_file(Path(path)) if path else "",
            "data_contract_mapping_hash": (
                FingerprintCalculator._get_data_contract_mapping_hash()
            ),
        }
        return FingerprintCalculator._to_fingerprint_hash(signature)

    # --- hash helpers -----------------------------------------------------

    @staticmethod
    def _to_fingerprint_hash(signature: Dict[str, Any]) -> str:
        canonical = json.dumps(
            signature,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_file(path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _get_database_type() -> str:
        try:
            cfg = ProjectContext.config.load_database_config()
            return str(cfg.get("database_type") or "").strip().lower()
        except Exception:
            return "unknown"

    @staticmethod
    def _get_data_contract_mapping_hash() -> str:
        core_mapping_hash = ""
        try:
            dc_mapping_module = importlib.import_module(
                "core.modules.data_contract.core.registry.mapping"
            )
            dc_mapping_file = inspect.getsourcefile(dc_mapping_module)
            if dc_mapping_file:
                core_mapping_hash = FingerprintCalculator._hash_file(Path(dc_mapping_file))
        except Exception:
            core_mapping_hash = ""

        userspace_mapping_hash = ""
        try:
            userspace_mapping_file = ProjectContext.path.get_data_contract_mapping_path()
            if userspace_mapping_file.exists():
                userspace_mapping_hash = FingerprintCalculator._hash_file(
                    Path(userspace_mapping_file)
                )
        except Exception:
            userspace_mapping_hash = ""

        return FingerprintCalculator._to_fingerprint_hash(
            {
                "core_mapping_hash": core_mapping_hash,
                "userspace_mapping_hash": userspace_mapping_hash,
            }
        )


__all__ = ["FingerprintCalculator", "FingerprintResult"]
