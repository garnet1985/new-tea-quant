"""DataKey Discovery 服务（扫描所有 DataKey 文件，建立 registry）。"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Dict, List

from .base_data_key import BaseDataKey

logger = logging.getLogger(__name__)


class DataKeyDiscovery:
    """DataKey Discovery 服务。

    职责：
    1. 扫描 data_keys/ 目录下的所有子文件夹
    2. 动态导入每个子文件夹的 key.py
    3. 提取导出的 {DATA_KEY_NAME}_DATA_KEY 实例
    4. 建立 registry（key -> DataKey 实例的映射）
    """

    @staticmethod
    def discover_all_data_keys() -> Dict[str, BaseDataKey]:
        """扫描所有 DataKey 文件，返回 key -> DataKey 实例的映射。

        Returns:
            Dict[str, BaseDataKey]: key -> DataKey 实例的映射

        流程：
        1. 扫描 data_keys/ 目录下的所有子文件夹
        2. 动态导入每个子文件夹的 key.py
        3. 提取导出的 {DATA_KEY_NAME}_DATA_KEY 实例
        4. 建立 registry
        """
        registry: Dict[str, BaseDataKey] = {}

        # 获取 data_keys 目录路径
        data_keys_dir = Path(__file__).parent

        # 扫描所有子文件夹
        for sub_dir in data_keys_dir.iterdir():
            if not sub_dir.is_dir():
                continue

            # 跳过非 DataKey 目录（如 __pycache__）
            if sub_dir.name.startswith('_') or sub_dir.name.startswith('.'):
                continue

            # 检查是否有 key.py 文件
            key_file = sub_dir / 'key.py'
            if not key_file.exists():
                logger.warning(f"子文件夹 {sub_dir.name} 缺少 key.py 文件，跳过")
                continue

            # 动态导入 key.py
            try:
                module_name = f"core.modules.data_contract.core.data_keys.{sub_dir.name}.key"
                module = importlib.import_module(module_name)

                # 提取导出的 DataKey 实例（查找以 _DATA_KEY 结尾的变量）
                for attr_name in dir(module):
                    if attr_name.endswith('_DATA_KEY') and not attr_name.startswith('_'):
                        data_key_instance = getattr(module, attr_name)

                        # 验证是否为 BaseDataKey 实例
                        if isinstance(data_key_instance, BaseDataKey):
                            key = data_key_instance.key
                            registry[key] = data_key_instance
                            logger.debug(f"发现 DataKey: {key} -> {attr_name}")
                        else:
                            logger.warning(f"{attr_name} 不是 BaseDataKey 实例，跳过")

            except Exception as e:
                logger.error(f"导入 {sub_dir.name}.key 失败: {e}")
                continue

        logger.info(f"Discovery 完成：发现 {len(registry)} 个 DataKey")
        return registry

    @staticmethod
    def list_all_data_key_names() -> List[str]:
        """列出所有 DataKey 名称。

        Returns:
            List[str]: 所有 DataKey 名称列表
        """
        registry = DataKeyDiscovery.discover_all_data_keys()
        return list(registry.keys())


# 全局 Registry（单例）
_GLOBAL_REGISTRY: Dict[str, BaseDataKey] = {}


def get_registry() -> Dict[str, BaseDataKey]:
    """获取全局 Registry（单例）。

    Returns:
        Dict[str, BaseDataKey]: key -> DataKey 实例的映射
    """
    if not _GLOBAL_REGISTRY:
        _GLOBAL_REGISTRY = DataKeyDiscovery.discover_all_data_keys()
    return _GLOBAL_REGISTRY


def get_data_key(key: str) -> BaseDataKey:
    """根据 key 获取 DataKey 实例。

    Args:
        key: DataKey 的唯一标识符（如 'stock.list'）

    Returns:
        BaseDataKey: DataKey 实例

    Raises:
        KeyError: 如果 key 不存在
    """
    registry = get_registry()
    if key not in registry:
        raise KeyError(f"DataKey {key} 不存在")
    return registry[key]


def get_loader(key: str) -> type:
    """根据 key 获取 Loader 类。

    Args:
        key: DataKey 的唯一标识符（如 'stock.list'）

    Returns:
        type: Loader 类

    Raises:
        KeyError: 如果 key 不存在
    """
    data_key = get_data_key(key)
    return data_key.loader


__all__ = [
    'DataKeyDiscovery',
    'get_registry',
    'get_data_key',
    'get_loader',
]