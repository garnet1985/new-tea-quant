#!/usr/bin/env python3
"""
Adapter Validator - Adapter 验证器

职责：
- 验证 adapter 是否存在且可用
"""

from typing import Tuple
import importlib
import inspect
import logging

from .base_adapter import BaseOpportunityAdapter

logger = logging.getLogger(__name__)


def validate_adapter(adapter_name: str) -> Tuple[bool, str]:
    """
    验证 adapter 是否可用
    
    Args:
        adapter_name: 适配器名称
    
    Returns:
        (is_valid, error_message): 
            - is_valid: True 表示可用，False 表示不可用
            - error_message: 如果不可用，返回错误信息；如果可用，返回空字符串
    """
    if not adapter_name:
        return False, "适配器名称不能为空"
    
    # 尝试加载 adapter 模块
    module_path = f"userspace.adapters.{adapter_name}.adapter"
    
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        return False, f"无法找到适配器模块: {module_path}"
    except Exception as exc:
        return False, f"加载适配器模块异常: {exc}"
    
    # 查找继承自 BaseOpportunityAdapter 的类
    adapter_class = None
    for _, obj in inspect.getmembers(module):
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseOpportunityAdapter)
            and obj is not BaseOpportunityAdapter
        ):
            adapter_class = obj
            break
    
    if adapter_class is None:
        return False, f"在模块 {module_path} 中未找到继承 BaseOpportunityAdapter 的类"
    
    # 验证类是否有 process 方法
    if not hasattr(adapter_class, 'process'):
        return False, f"适配器类 {adapter_class.__name__} 没有实现 process 方法"
    
    # 尝试实例化（不传参数）
    try:
        instance = adapter_class()
        # 验证 process 方法是否可调用
        if not callable(getattr(instance, 'process', None)):
            return False, f"适配器类 {adapter_class.__name__} 的 process 方法不可调用"
    except Exception as exc:
        return False, f"实例化适配器失败: {exc}"
    
    return True, ""
