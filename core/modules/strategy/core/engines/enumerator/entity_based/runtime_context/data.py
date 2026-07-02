"""entity_based 模式 hook data context。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.services.discovery.data.discovered_strategy import StrategyInfo


@dataclass
class EntityBasedDataContext:
    """entity_based 模式专用 DataContext（用户hooks数据）。

    职责：
    - 主进程：global数据注入（验证指纹后）
    - 子进程worker：load_contracts（需要job input）
    """

    # 策略信息
    strategy_id: str = ""

    # 数据存储（global数据）
    global_data: Dict[str, Any] = field(default_factory=dict)    # global数据（主进程注入）
    global_data_meta: Dict[str, Any] = field(default_factory=dict)    # global数据meta信息

    # Entity信息（子进程worker使用）
    entity_id: Optional[str] = None
    entity_info: Dict[str, Any] = field(default_factory=dict)

    # 其他信息
    extra: Dict[str, Any] = field(default_factory=dict)
    calendar: Dict[str, Any] = field(default_factory=dict)
    opportunity: Optional[Any] = None

    @classmethod
    def init(cls, strategy_info: StrategyInfo, settings_obj: StrategySettings, global_data_cache: Optional[Dict[str, Any]] = None) -> EntityBasedDataContext:
        """初始化data context（加载global data）。

        Args:
            strategy_info: 策略信息（基础信息）
            settings_obj: validated settings对象（验证过的settings）
            global_data_cache: global数据缓存（包含global_data和global_meta）
        """

        # 1. 尝试从global_data_cache加载
        global_data = {}
        global_data_meta = {}

        if global_data_cache and "global_data" in global_data_cache:
            global_data = global_data_cache["global_data"]
            global_data_meta = global_data_cache.get("global_meta", {})
            # TODO: 实现共享内存方案
        else:
            # 2. 没有cache就preload（简化版）
            # TODO: 实现GlobalDataPreloader.preload()
            # 暂时使用空数据，后续实现
            pass

        return cls(
            strategy_id=strategy_info.unique_relative_path,
            global_data=global_data,
            global_data_meta=global_data_meta,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """数据访问接口（hooks使用）。"""
        return self.global_data.get(key, default)

    def fill_global_data(self, global_data: Dict[str, Any]) -> None:
        """填充全局数据（主进程，验证指纹后）。"""
        self.global_data.update(global_data)

    def load_contracts(self, entity_ids: List[str]) -> None:
        """加载contracts数据（子进程worker，需要entity_ids）。"""
        # TODO: 实现contracts加载逻辑（根据entity_ids加载）
        pass


__all__ = ["EntityBasedDataContext"]


__all__ = ["EntityBasedDataContext"]