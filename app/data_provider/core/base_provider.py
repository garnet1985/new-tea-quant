#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BaseProvider - Provider统一接口

所有数据源Provider必须实现此接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Dependency:
    """
    依赖声明
    
    Attributes:
        provider: 依赖的Provider名称
        data_types: 依赖的数据类型列表
        when: 依赖时机（before_renew | runtime）
        required: 是否必需
        pass_data: 是否需要传递数据到context
    """
    provider: str
    data_types: List[str]
    when: str = "before_renew"  # before_renew | runtime
    required: bool = True
    pass_data: bool = False


@dataclass
class ProviderInfo:
    """
    Provider元数据
    
    用于：
    - 依赖解析
    - 路由决策
    - 文档生成
    """
    name: str
    version: str = "1.0.0"
    provides: List[str] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    requires_auth: bool = False


@dataclass
class ExecutionContext:
    """
    执行上下文
    
    包含Provider执行时需要的所有信息
    """
    end_date: str  # 截止日期（YYYYMMDD）
    stock_list: Optional[List[str]] = None  # 股票列表
    dependencies: Optional[Dict[str, Any]] = None  # 依赖数据
    config: Optional[Dict[str, Any]] = None  # 额外配置


class BaseProvider(ABC):
    """
    Provider 基类（统一接口）
    
    所有数据源Provider必须实现此接口
    """
    
    def __init__(self, data_manager, rate_limit_registry, is_verbose: bool = False):
        """
        初始化Provider
        
        Args:
            data_manager: DataManager实例（访问数据库和DataService）
            rate_limit_registry: RateLimitRegistry实例（API限流注册表）
            is_verbose: 是否详细日志
        """
        self.data_manager = data_manager
        self.rate_limit_registry = rate_limit_registry
        self.is_verbose = is_verbose
    
    # ===== 必须实现的方法 =====
    
    @abstractmethod
    def get_provider_info(self) -> ProviderInfo:
        """
        返回Provider元数据
        
        用于：
        - 依赖解析
        - 路由决策
        - 文档生成
        
        Returns:
            ProviderInfo: Provider元数据
        """
        pass
    
    @abstractmethod
    async def renew_all(self, end_date: str, context: Optional[ExecutionContext] = None):
        """
        更新此Provider提供的所有数据类型
        
        Args:
            end_date: 截止日期（YYYYMMDD）
            context: 执行上下文（包含依赖数据等）
        """
        pass
    
    @abstractmethod
    def supports_data_type(self, data_type: str) -> bool:
        """
        是否支持某种数据类型
        
        Args:
            data_type: 数据类型名称
        
        Returns:
            bool: 是否支持
        """
        pass
    
    # ===== 可选实现的方法 =====
    
    async def renew_data_type(
        self, 
        data_type: str, 
        end_date: str, 
        context: Optional[ExecutionContext] = None
    ):
        """
        更新指定数据类型（可选）
        
        如果不实现，默认调用 renew_all()
        
        Args:
            data_type: 数据类型名称
            end_date: 截止日期
            context: 执行上下文
        """
        return await self.renew_all(end_date, context)
    
    def validate_dependencies(self, context: Optional[ExecutionContext]) -> bool:
        """
        验证依赖是否满足（可选）
        
        Args:
            context: 执行上下文
        
        Returns:
            bool: 依赖是否满足
        """
        info = self.get_provider_info()
        
        for dep in info.dependencies:
            if dep.required and dep.pass_data:
                # 检查context中是否有所需的依赖数据
                if not context or not context.dependencies:
                    return False
                
                for data_type in dep.data_types:
                    if data_type not in context.dependencies:
                        return False
        
        return True

