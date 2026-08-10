"""动态加载 userspace opportunity adapter 类（内部）。"""

from __future__ import annotations

import importlib
import inspect
from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.adapter.core.base_adapter import BaseOpportunityAdapter


class AdapterLoader:
    """按约定路径加载 ``BaseOpportunityAdapter`` 子类。"""

    @staticmethod
    def module_path(adapter_name: str) -> str:
        return f"userspace.extensions.adapters.{adapter_name}.adapter"

    @staticmethod
    def settings_module_path(adapter_name: str) -> str:
        return f"userspace.extensions.adapters.{adapter_name}.settings"

    @staticmethod
    def find_adapter_class(module: object) -> Optional[Type["BaseOpportunityAdapter"]]:
        """取模块中第一个合法子类（非基类本身）。"""
        from core.modules.adapter.core.base_adapter import BaseOpportunityAdapter

        for _, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseOpportunityAdapter)
                and obj is not BaseOpportunityAdapter
            ):
                return obj
        return None

    @staticmethod
    def load_class(adapter_name: str) -> Optional[Type["BaseOpportunityAdapter"]]:
        """导入并返回 adapter 类；失败返回 ``None``。"""
        name = str(adapter_name or "").strip()
        if not name:
            return None
        try:
            module = importlib.import_module(AdapterLoader.module_path(name))
        except Exception:
            return None
        return AdapterLoader.find_adapter_class(module)


__all__ = ["AdapterLoader"]
