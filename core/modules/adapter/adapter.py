"""Adapter 门面 — 校验 / 加载 userspace opportunity adapter。"""

from __future__ import annotations

from typing import Optional, Tuple, Type

from core.modules.adapter.core.adapter_validator import AdapterValidator
from core.modules.adapter.core.loader import AdapterLoader


class Adapter:
    """Scanner 后续处理适配器门面。"""

    @staticmethod
    def validate(adapter_name: str) -> Tuple[bool, str]:
        """验证 adapter 是否可加载且实现合法。"""
        return AdapterValidator.validate(adapter_name)

    @staticmethod
    def load_class(adapter_name: str) -> Optional[Type]:
        """按名加载 ``BaseOpportunityAdapter`` 子类；失败返回 ``None``。"""
        return AdapterLoader.load_class(adapter_name)


__all__ = ["Adapter"]
