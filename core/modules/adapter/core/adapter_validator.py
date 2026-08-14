"""Adapter Validator — 校验 userspace adapter 是否可用。"""

from __future__ import annotations

import importlib
import logging
from typing import Tuple

from core.modules.adapter.core.loader import AdapterLoader

logger = logging.getLogger(__name__)


class AdapterValidator:
    """校验 userspace adapter 模块是否可用。"""

    @staticmethod
    def validate(adapter_name: str) -> Tuple[bool, str]:
        """
        验证 adapter 是否可用。

        Returns:
            (is_valid, error_message)
        """
        if not adapter_name:
            return False, "适配器名称不能为空"

        module_path = AdapterLoader.module_path(adapter_name)

        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            if str(getattr(exc, "name", "") or "") == module_path:
                return False, f"无法找到适配器模块: {module_path}"
            missing = str(getattr(exc, "name", "") or exc)
            return False, f"适配器依赖缺失: {missing}"
        except Exception as exc:
            return False, f"加载适配器模块异常: {exc}"

        adapter_class = AdapterLoader.find_adapter_class(module)
        if adapter_class is None:
            return False, f"在模块 {module_path} 中未找到继承 BaseOpportunityAdapter 的类"

        if not hasattr(adapter_class, "process"):
            return False, f"适配器类 {adapter_class.__name__} 没有实现 process 方法"

        try:
            instance = adapter_class()
            if not callable(getattr(instance, "process", None)):
                return False, f"适配器类 {adapter_class.__name__} 的 process 方法不可调用"
        except Exception as exc:
            return False, f"实例化适配器失败: {exc}"

        return True, ""


__all__ = ["AdapterValidator"]
