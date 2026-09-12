"""JSON / 行 payload 的标量强制转换（无 IO、无业务语义）。

消费者: enum_result_contract、artifacts 行模型
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional, Tuple


class ValueCoerce:
    """空串 / Enum / 松散 JSON 值 → str/float/int/bool。"""

    @staticmethod
    def as_str(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, Enum):
            return str(value.value).strip()
        return str(value).strip()

    @staticmethod
    def as_float(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def as_int(value: Any, default: int = 0) -> int:
        if value is None or value == "":
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def as_optional_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def as_optional_bool(value: Any) -> Optional[bool]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ("true", "1", "yes"):
            return True
        if text in ("false", "0", "no"):
            return False
        return None

    @staticmethod
    def as_str_tuple(value: Any) -> Tuple[str, ...]:
        if value is None or value == "":
            return ()
        if isinstance(value, str):
            text = value.strip()
            return (text,) if text else ()
        if isinstance(value, (list, tuple)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return ()


__all__ = ["ValueCoerce"]
