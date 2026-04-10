"""
按 `data_id` 注册 **resolver（load 物化）**。

- 约定：`resolver(data_entity: DataEntity, **kwargs) -> Any`；kwargs 由外层编排传入。
- **全局唯一 id**、重复注册 fail-fast 等规则见 `CONCEPTS.md` §9–§10。
- 与 **规则类路由**（`registry.route_registry`）并行；后续可合并为一套注册单元。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Protocol


class Resolver(Protocol):
    """第一个位置参数为 `DataEntity`；注解用 `Any` 避免与 `data_entity` 循环导入。"""

    def __call__(self, entity: Any, **kwargs: Any) -> Any: ...


class ResolverRegistry:
    __slots__ = ("_by_id",)

    def __init__(self) -> None:
        self._by_id: Dict[str, Resolver] = {}

    def register(self, data_id: str, resolver: Resolver) -> None:
        if data_id in self._by_id:
            raise ValueError(f"duplicate resolver registration for data_id={data_id!r}")
        self._by_id[data_id] = resolver

    def resolve(self, data_id: str) -> Resolver:
        r = self._by_id.get(data_id)
        if r is None:
            raise KeyError(f"ResolverRegistry: no resolver registered for data_id={data_id!r}")
        return r

    def has(self, data_id: str) -> bool:
        return data_id in self._by_id


# 便于类型标注：resolver 可为任意可调用
ResolverFn = Callable[..., Any]
