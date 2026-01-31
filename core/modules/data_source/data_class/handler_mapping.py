from dataclasses import dataclass
from typing import Any, Dict, List

from loguru import logger

from core.modules.data_source.reserved_dependencies import RESERVED_DEPENDENCY_KEYS


@dataclass
class HandlerMapping:

    def __init__(self, data_sources: Dict[str, Dict[str, Any]]):
        self.data_sources = data_sources
        self.enabled_cache = {}
        self._validate_and_cache_enabled()

    def _validate_and_cache_enabled(self):
        for data_source_key, data_source_info in self.data_sources.items():
            if data_source_key in RESERVED_DEPENDENCY_KEYS:
                raise ValueError(
                    f"mapping 中 data source key 不能使用保留字: {data_source_key}。"
                    f"保留关键字仅用于 depends_on，不可作为数据源名: {sorted(RESERVED_DEPENDENCY_KEYS)}"
                )
            if not isinstance(data_source_info, dict):
                raise ValueError(f"mapping 中 {data_source_key} 格式错误，应是字典格式.")

            if not data_source_info.get("handler"):
                raise ValueError(f"mapping 中缺失或错误配置了 {data_source_key} 的 handler 属性.")

            if not data_source_info.get("is_enabled", True):
                logger.info(f"mapping 中 {data_source_key} 配置了 is_enabled 为 false，跳过.")
                continue

            self.enabled_cache[data_source_key] = data_source_info



    def get_enabled(self) -> Dict[str, Dict[str, Any]]:
        return self.enabled_cache

    def get_handler_info(self, data_source_key: str) -> Dict[str, Any]:
        info = self.data_sources.get(data_source_key, None)
        if not info:
            logger.warning(f"在已启用的 handler 中未找到 key：{data_source_key}")
        return info

    def get_depend_on_data_source_names(self, data_source_key: str) -> List[str]:
        info = self.get_handler_info(data_source_key)
        return info.get("depends_on", [])

    def is_dependency_for_downstream(self, data_source_key: str) -> bool:
        """
        检查某个 data source 是否被其他 data source 依赖。

        用于决定是否需要缓存该 data source 的执行结果。
        """
        for enabled_key, enabled_info in self.enabled_cache.items():
            if enabled_key == data_source_key:
                continue
            depends_on = enabled_info.get("depends_on", [])
            if data_source_key in depends_on:
                return True
        
        return False
