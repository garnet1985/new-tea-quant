"""模拟三步共享：指纹解析（进入引擎前）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.engines.shared.services.finger_print.fingerprint import (
    Fingerprint,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)


@dataclass(frozen=True)
class SimulationFingerprints:
    """一次模拟请求的共享指纹与有效 settings。

    边界:
    - 负责: 供编排层查缓存、供各 Pipeline 写缓存
    - 不负责: 缓存读写本身
    """

    settings_fp: str
    env_fp: str
    settings_diff: Dict[str, Any]
    effective_settings: StrategySettings
    entity_ids: List[str]


class SimulationFingerprintResolver:
    """在进入任一回测引擎前解析 settings_fp / env_fp。"""

    @staticmethod
    def resolve(
        strategy_info: EnabledStrategyInfo,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> SimulationFingerprints:
        effective_settings, settings_diff = StrategySettings.calculate_effective_settings(
            disk_settings=strategy_info.settings,
            user_settings=runtime_settings or {},
        )
        cache = GlobalEntityCache(effective_settings)
        entity_ids = cache.init_system_globals().get_stock_ids()
        settings_fp = Fingerprint.to_settings_diff_fingerprint(settings_diff, entity_ids)
        env_fp = Fingerprint.to_env_fingerprint(
            strategy_info=strategy_info,
            effective_settings=effective_settings,
            entity_ids=entity_ids,
        )
        return SimulationFingerprints(
            settings_fp=settings_fp,
            env_fp=env_fp,
            settings_diff=settings_diff,
            effective_settings=effective_settings,
            entity_ids=list(entity_ids),
        )


__all__ = ["SimulationFingerprints", "SimulationFingerprintResolver"]
