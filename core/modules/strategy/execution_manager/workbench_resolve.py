"""工作台步骤：合法 step 归一化 + API settings → ``DiscoveredStrategy``。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from core.infra.project_context.path_manager import PathManager
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import DiscoveredStrategy
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
from core.modules.strategy.launcher.run_service import StrategySettingsService

_VALID_STEPS = frozenset({"enum", "price", "capital"})


def normalize_step(step: str) -> Optional[str]:
    s = str(step or "").strip().lower()
    return s if s in _VALID_STEPS else None


def resolve_discovered_strategy(
    strategy_name: str, api_settings: Dict[str, Any]
) -> Tuple[Optional[DiscoveredStrategy], Optional[str]]:
    folder = PathManager.userspace() / "strategies" / strategy_name
    base = StrategyDiscoveryHelper.load_strategy(folder)
    if base is None:
        return None, "策略不存在或无法加载"

    normalized, err = StrategySettingsService.normalize_runtime_settings(
        strategy_name=strategy_name,
        api_settings=api_settings,
    )
    if err or not normalized:
        return None, err or "settings 校验失败"

    st = StrategySettings(raw_settings=dict(normalized))
    vr = st.validate()
    if not vr.is_usable():
        return None, "settings 校验失败"

    discovered = DiscoveredStrategy(
        name=base.name,
        folder=base.folder,
        worker_class=base.worker_class,
        worker_module_path=base.worker_module_path,
        worker_class_name=base.worker_class_name,
        settings=st,
    )
    discovered.validate_required_fields()
    return discovered, None


__all__ = ["normalize_step", "resolve_discovered_strategy"]
