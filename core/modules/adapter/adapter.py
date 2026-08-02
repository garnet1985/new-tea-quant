"""Adapter 门面 — 校验 userspace opportunity adapter。"""

from __future__ import annotations

from typing import Tuple

from core.modules.adapter.adapter_validator import AdapterValidator


class Adapter:
    """Scanner 后续处理适配器门面。"""

    @staticmethod
    def validate(adapter_name: str) -> Tuple[bool, str]:
        """验证 adapter 是否可加载且实现合法。"""
        return AdapterValidator.validate(adapter_name)


__all__ = ["Adapter"]
