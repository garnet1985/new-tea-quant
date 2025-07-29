#!/usr/bin/env python3
"""
策略抽象基类
定义所有策略必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any      

class BaseStrategy(ABC):
    def __init__(self):
        self.strategy_name = None
        self.strategy_description = None
        self.prefix = None
        self.is_enabled = False

    def check_params(self):
        if self.strategy_name is None:
            raise ValueError("Strategy name is required")
        if self.strategy_description is None:
            raise ValueError("Strategy description is required")
        if self.prefix is None:
            raise ValueError("Prefix is required")

    def get_strategy_name(self):
        return self.strategy_name

    def get_strategy_description(self):
        return self.strategy_description

    def get_prefix(self):
        return self.prefix

    def enable(self):
        self.is_enabled = True

    def disable(self):
        self.is_enabled = False

    @abstractmethod
    def test(self):
        """测试策略"""
        pass
    
    @abstractmethod
    def scan(self):
        """扫描机会"""
        pass
    
    @abstractmethod
    def present(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        展示数据
        """
        pass