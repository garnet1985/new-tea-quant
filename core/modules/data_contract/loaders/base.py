from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Sequence


class BaseLoader(ABC):
    """所有业务 loader 的抽象基类。"""

    @abstractmethod
    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        """根据参数与上下文加载数据。"""
        raise NotImplementedError

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """批量加载；默认对每个 entity 调用 ``load``。"""
        out: dict[str, Any] = {}
        for raw_id in entity_ids:
            eid = str(raw_id).strip()
            if not eid:
                continue
            ctx: dict[str, Any] = dict(context or {})
            ctx.setdefault("entity_id", eid)
            ctx.setdefault("stock_id", eid)
            ctx.setdefault("id", eid)
            out[eid] = self.load(params, ctx)
        return out

