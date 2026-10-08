"""命中时的 as-of 当日一片：声明数据的最后一行，不是整段历史。

用户 ``capture`` 同名覆盖。只收标量，不收嵌套袋（raw / hfq 等）。
"""
from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional

from core.modules.strategy.core.hooks.hook_params import StrategyContext

_SKIP_FIELDS = frozenset(
    {
        "date",
        "datetime",
        "time",
        "raw",
        "hfq",
        "qfq",
        "stock_id",
        "symbol",
        "code",
        "id",
        "name",
    }
)


class AsOfSnapshot:
    """命中现场：base 最后一根 + 各 required 最后一行。"""

    @classmethod
    def build(cls, ctx: StrategyContext) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        base_key = str(ctx.base_data_key or "").strip()
        base_row = ctx.record_of_today
        if isinstance(base_row, dict):
            cls._absorb(out, base_row, prefix="")
        try:
            declarations = ctx.settings.data.issue_declarations()
        except (TypeError, ValueError, AttributeError):
            declarations = []
        items = ctx.data.items if isinstance(ctx.data.items, Mapping) else {}
        for decl in declarations:
            if not isinstance(decl, dict):
                continue
            data_key = str(decl.get("data_key") or "").strip()
            if not data_key or data_key == base_key:
                continue
            rows = items.get(data_key)
            if not isinstance(rows, list) or not rows:
                continue
            last = rows[-1]
            if isinstance(last, dict):
                cls._absorb(out, last, prefix=data_key)
        return out

    @classmethod
    def merge(
        cls,
        auto: Mapping[str, Any],
        captures: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """自动 as-of 在下，用户 capture 同名覆盖。"""
        out = dict(auto or {})
        if isinstance(captures, Mapping):
            for key, value in captures.items():
                name = str(key or "").strip()
                if not name:
                    continue
                out[name] = value
        return out

    @classmethod
    def _absorb(
        cls,
        out: Dict[str, Any],
        row: Mapping[str, Any],
        *,
        prefix: str,
    ) -> None:
        for key, value in row.items():
            field = str(key or "").strip()
            if not field or field in _SKIP_FIELDS:
                continue
            scalar = cls._numeric_scalar(value)
            if scalar is None:
                continue
            name = f"{prefix}.{field}" if prefix else field
            out[name] = scalar

    @staticmethod
    def _numeric_scalar(value: Any) -> Optional[float]:
        if value is None or isinstance(value, (bool, dict, list, tuple)):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(number) or math.isinf(number):
            return None
        return number
