from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Optional

from .contract_scope import ContractScope


@dataclass(frozen=True)
class BaseContract(ABC):
    """
    Level-0 **规则类** contract 基类（MVP）。

    仅含必填 identity；`display_name` / `context` 在具体子类末尾声明（满足 dataclass 字段顺序约束）。
    子类实现 `scope` 与 **`validate_raw`**（对裸数据 fail-closed 校验）。
    与 `CONCEPTS.md` 中「数据依赖壳」叙事里的 Contract **同名不同义**；必要时可再拆类型名。
    """

    contract_id: str
    name: str

    @property
    @abstractmethod
    def scope(self) -> ContractScope: ...

    @abstractmethod
    def validate_raw(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> Any:
        """对已有裸数据做形态/字段校验；成功则返回可供下游使用的数据（常为 raw 本身）。"""

    def with_context(self, **extra: Any) -> BaseContract:
        merged: Dict[str, Any] = dict(getattr(self, "context", None) or {})
        merged.update(extra)
        return replace(self, context=merged)
