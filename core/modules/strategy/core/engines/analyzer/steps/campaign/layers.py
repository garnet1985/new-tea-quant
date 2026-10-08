"""按层挑子类。各步门面共用，避免每层一个空文件。"""
from __future__ import annotations

from typing import Any, Type, TypeVar

_T = TypeVar("_T")


def layer_key(layer: Any) -> str:
    """把层枚举或字符串收成层名。"""
    return str(getattr(layer, "value", layer) or "").strip()


def pick_layer(mapping: dict, layer: Any, default: Type[_T]) -> Type[_T]:
    """按层名取子类，没有则用默认。"""
    found = mapping.get(layer_key(layer))
    return default if found is None else found


def declare_layer(name: str, base: type, layer: str, kind: Any, **attrs: Any) -> type:
    """生成带层名和模拟种类的子类。"""
    namespace = {"LAYER": layer, "KIND": kind, "__doc__": f"{layer} 层步骤。"}
    namespace.update(attrs)
    return type(name, (base,), namespace)
