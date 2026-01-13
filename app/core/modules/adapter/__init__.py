#!/usr/bin/env python3
"""
Adapter 模块

职责：
- 定义 BaseOpportunityAdapter 基类
- 提供 adapter 的基础功能
- 提供 adapter 验证方法
"""

from .base_adapter import BaseOpportunityAdapter
from .adapter_validator import validate_adapter

__all__ = ['BaseOpportunityAdapter', 'validate_adapter']
