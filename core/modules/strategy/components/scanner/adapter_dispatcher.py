#!/usr/bin/env python3
"""
AdapterDispatcher - 适配器分发器

职责：
- 从 userspace 动态加载 adapter
- 调用 adapter 处理机会列表
"""

from dataclasses import dataclass
from typing import Any, List, Optional
import importlib
import inspect
import logging

from core.modules.adapter import BaseOpportunityAdapter

logger = logging.getLogger(__name__)


@dataclass
class AdapterDispatcher:
    """适配器分发器"""
    
    strategy_name: str
    
    def dispatch(
        self,
        adapter_names: List[str],
        opportunities: List[Opportunity],
        context: dict[str, Any]
    ) -> None:
        """
        分发机会到指定的 adapters（支持多个）
        
        如果所有 adapter 都失败，会使用默认输出。
        
        Args:
            adapter_names: 适配器名称列表（如 ["console", "webhook"]），可以为空
            opportunities: 机会列表
            context: 上下文信息
        """
        success_count = 0
        
        # 如果没有配置 adapter，直接使用默认输出
        if not adapter_names:
            logger.info("[AdapterDispatcher] 未配置 adapter，使用默认输出")
            BaseOpportunityAdapter.default_output(opportunities, context)
            return
        
        # 尝试调用每个 adapter
        for adapter_name in adapter_names:
            adapter_class = self._load_adapter_class(adapter_name)
            if adapter_class is None:
                logger.warning(
                    f"[AdapterDispatcher] 无法加载 adapter: {adapter_name}, "
                    "跳过"
                )
                continue
            
            try:
                # 实例化 adapter（无参数构造）
                adapter = adapter_class()
                
                # 调用 process 方法
                adapter.process(opportunities, context)
                success_count += 1
                
            except Exception as e:
                logger.error(
                    f"[AdapterDispatcher] 调用 adapter {adapter_name} 失败: {e}",
                    exc_info=True
                )
        
        # 如果所有 adapter 都失败，使用默认输出
        if success_count == 0:
            logger.warning(
                "[AdapterDispatcher] 所有配置的 adapter 都失败，使用默认输出"
            )
            BaseOpportunityAdapter.default_output(opportunities, context)
    
    def _load_adapter_class(
        self,
        adapter_name: str
    ) -> Optional[type[BaseOpportunityAdapter]]:
        """
        动态加载 adapter 类
        
        Args:
            adapter_name: 适配器名称
        
        Returns:
            Adapter 类，如果加载失败返回 None
        """
        # Adapter 放在 userspace/adapters/{adapter_name}/adapter.py
        module_path = f"userspace.adapters.{adapter_name}.adapter"
        
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            logger.warning(
                f"[AdapterDispatcher] 无法加载 adapter 模块: {module_path}"
            )
            return None
        except Exception as exc:
            logger.warning(
                f"[AdapterDispatcher] 加载 adapter 模块异常: {module_path}, error={exc}"
            )
            return None
        
        # 查找继承自 BaseOpportunityAdapter 的类
        for _, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseOpportunityAdapter)
                and obj is not BaseOpportunityAdapter
            ):
                return obj
        
        logger.warning(
            f"[AdapterDispatcher] 在模块 {module_path} 中未找到继承 BaseOpportunityAdapter 的类"
        )
        return None
