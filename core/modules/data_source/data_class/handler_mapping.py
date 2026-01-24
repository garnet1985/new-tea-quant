from dataclasses import dataclass
from typing import Any, Dict, List

from loguru import logger

@dataclass
class HandlerMapping:

    def __init__(self, data_sources: Dict[str, Dict[str, Any]]):
        self.data_sources = data_sources
        self._validate_and_cache_enabled()

    def _validate_and_cache_enabled(self):
        for data_source_name, data_source_info in self.data_sources.items():
            if not isinstance(data_source_info, dict):
                raise ValueError(f"mapping.json 中 {data_source_name} 格式错误，应是字典格式.")

            if not data_source_info.get("handler"):
                raise ValueError(f"mapping.json 中缺失或错误配置了 {data_source_name} 的 handler 属性.")

            if not data_source_info.get("is_enabled", True):
                logger.info(f"mapping.json 中 {data_source_name} 配置了 is_enabled 为 false，跳过.")

            self.enabled_cache[data_source_name] = data_source_info


    def get_enabled(self) -> Dict[str, Dict[str, Any]]:
        return self.enabled_cache

    def get_handler_info(self, data_source_name: str) -> Dict[str, Any]:
        info = self.data_sources.get(data_source_name, None)
        if not info:
            logger.warning(f"在已经开启的handler中没有找到名字是：{data_source_name} 的配置")
        return info

    def get_depend_on_data_source_names(self, data_source_name: str) -> List[str]:
        info = self.get_handler_info(data_source_name)
        return info.get("depends_on", [])
