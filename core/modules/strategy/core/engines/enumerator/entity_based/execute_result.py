"""entity_based execute_fn 返回值契约。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class EntityBasedExecuteResult:
    """单股枚举 execute_fn 结果（成功或失败均用此类表达）。"""

    success: bool
    entity_id: str
    entity_name: str
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    opportunity_count: int = 0
    skipped_short_data: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "success": self.success,
            "entity_id": self.entity_id,
            "stock_id": self.entity_id,
            "stock_name": self.entity_name,
            "opportunities": list(self.opportunities),
            "opportunity_count": self.opportunity_count,
            "skipped_short_data": self.skipped_short_data,
        }
        if self.error:
            row["error"] = self.error
        return row

    @classmethod
    def completed(
        cls,
        *,
        entity_id: str,
        entity_name: str,
        opportunities: List[Dict[str, Any]],
        skipped_short_data: bool = False,
    ) -> EntityBasedExecuteResult:
        return cls(
            success=True,
            entity_id=entity_id,
            entity_name=entity_name,
            opportunities=list(opportunities),
            opportunity_count=len(opportunities),
            skipped_short_data=skipped_short_data,
        )

    @classmethod
    def failed(cls, *, entity_id: str, error: str) -> EntityBasedExecuteResult:
        name = entity_id.strip() or "unknown"
        return cls(
            success=False,
            entity_id=entity_id,
            entity_name=name,
            error=str(error),
        )


__all__ = ["EntityBasedExecuteResult"]
