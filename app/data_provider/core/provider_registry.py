#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ProviderRegistry - Provider注册表

职责：
1. 动态挂载/卸载Provider
2. 管理Provider生命周期
3. 构建数据类型索引
4. 提供查询接口
"""

from typing import Dict, List, Optional
from loguru import logger

from .base_provider import BaseProvider, ProviderInfo


class ProviderMetadata:
    """Provider元数据（用于注册表内部管理）"""
    
    def __init__(self, name: str, provides: List[str], dependencies: List = None, enabled: bool = True):
        self.name = name
        self.provides = provides or []
        self.dependencies = dependencies or []
        self.enabled = enabled


class ProviderRegistry:
    """
    Provider 注册表
    
    职责：
    1. 动态挂载/卸载Provider
    2. 管理Provider生命周期
    3. 构建数据类型索引
    4. 提供查询接口
    """
    
    def __init__(self):
        """初始化注册表"""
        self._providers: Dict[str, BaseProvider] = {}
        self._metadata: Dict[str, ProviderMetadata] = {}
        self._data_type_index: Dict[str, List[str]] = {}  # data_type -> [provider_names]
    
    def mount(self, name: str, provider: BaseProvider, metadata: Optional[ProviderMetadata] = None):
        """
        挂载Provider
        
        Args:
            name: Provider名称（如 'tushare'）
            provider: Provider实例
            metadata: Provider元数据（可选，如果不提供则从provider获取）
        """
        # 验证
        if not isinstance(provider, BaseProvider):
            raise TypeError(f"Provider must implement BaseProvider interface")
        
        # 获取元数据
        if not metadata:
            info = provider.get_provider_info()
            metadata = ProviderMetadata(
                name=info.name,
                provides=info.provides or [],
                dependencies=info.dependencies or []
            )
        
        # 注册
        self._providers[name] = provider
        self._metadata[name] = metadata
        
        # 更新索引
        for data_type in metadata.provides:
            if data_type not in self._data_type_index:
                self._data_type_index[data_type] = []
            if name not in self._data_type_index[data_type]:
                self._data_type_index[data_type].append(name)
        
        logger.info(
            f"✅ Provider '{name}' 已挂载，提供: {metadata.provides}"
        )
    
    def unmount(self, name: str):
        """
        卸载Provider
        
        Args:
            name: Provider名称
        """
        if name not in self._providers:
            logger.warning(f"⚠️  Provider '{name}' 未挂载")
            return
        
        # 清理索引
        metadata = self._metadata[name]
        for data_type in metadata.provides:
            if data_type in self._data_type_index:
                if name in self._data_type_index[data_type]:
                    self._data_type_index[data_type].remove(name)
        
        # 删除
        del self._providers[name]
        del self._metadata[name]
        
        logger.info(f"Provider '{name}' 已卸载")
    
    def get(self, name: str) -> Optional[BaseProvider]:
        """
        获取Provider实例
        
        Args:
            name: Provider名称
        
        Returns:
            BaseProvider: Provider实例，如果不存在返回None
        """
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """
        列出所有已挂载的Provider
        
        Returns:
            List[str]: Provider名称列表
        """
        return list(self._providers.keys())
    
    def get_providers_for(
        self, 
        data_type: str, 
        enabled_only: bool = True
    ) -> List[str]:
        """
        获取支持某数据类型的所有Provider
        
        Args:
            data_type: 数据类型
            enabled_only: 是否只返回启用的Provider
        
        Returns:
            List[str]: Provider名称列表
        """
        providers = self._data_type_index.get(data_type, [])
        
        if enabled_only:
            # 过滤禁用的Provider
            providers = [
                p for p in providers 
                if self._metadata[p].enabled
            ]
        
        return providers
    
    def get_metadata(self, name: str) -> Optional[ProviderMetadata]:
        """
        获取Provider元数据
        
        Args:
            name: Provider名称
        
        Returns:
            ProviderMetadata: 元数据，如果不存在返回None
        """
        return self._metadata.get(name)
    
    def has_provider(self, name: str) -> bool:
        """
        是否存在某个Provider
        
        Args:
            name: Provider名称
        
        Returns:
            bool: 是否存在
        """
        return name in self._providers
    
    def list_all_data_types(self) -> List[str]:
        """
        列出所有支持的data_type
        
        Returns:
            List[str]: data_type列表
        """
        return list(self._data_type_index.keys())

