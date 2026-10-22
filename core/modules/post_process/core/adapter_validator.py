"""校验 userspace adapter 可加载。"""

from __future__ import annotations

from typing import Tuple

from core.modules.post_process.core.adapter_loader import AdapterLoader


class AdapterValidator:
    @staticmethod
    def validate(adapter_name: str) -> Tuple[bool, str]:
        name = str(adapter_name or "").strip()
        if not name:
            return False, "adapter 名称不能为空"
        cls = AdapterLoader.load_class(name)
        if cls is None:
            return (
                False,
                f"无法加载 userspace.extensions.post_process.adapters.{name}.adapter "
                f"中的 BaseAdapter 子类",
            )
        if not callable(getattr(cls, "run", None)):
            return False, f"{cls.__name__} 缺少可调用的 run"
        try:
            cls()
        except Exception as exc:
            return False, f"实例化失败: {exc}"
        return True, ""


__all__ = ["AdapterValidator"]
