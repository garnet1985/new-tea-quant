"""Unified job payload templates (export dataclasses for JobBuilders)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EntitySpec:
    """单实体声明。"""

    id: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id).strip()}


@dataclass
class SharedDataSpec:
    """per-entity 共用数据声明（一个 data_key）。"""

    data_key: str
    params: Dict[str, Any] = field(default_factory=dict)
    start: str = ""
    end: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "params": dict(self.params),
            "indicators": dict(self.indicators),
        }
        if self.start:
            out["start"] = self.start
        if self.end:
            out["end"] = self.end
        return out


@dataclass
class JobPayloadTemplate:
    """策略侧 job payload 模版（数据声明 + 运行元数据）。

    边界:
    - 负责: 结构化字段与 to_dict，供 JobBuilder 组装
    - 不负责: 校验业务语义（由 BacktestJob.validate / 调用方保证）
    - 不归属: BacktestEngine（引擎只消费 jobs，不解释数据声明）
    """

    entity_specified: List[EntitySpec] = field(default_factory=list)
    entity_shared: Dict[str, SharedDataSpec] = field(default_factory=dict)
    global_keys: Dict[str, Any] = field(default_factory=dict)
    shm_info: Dict[str, Any] = field(default_factory=dict)
    strategy_info: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    output_recorder: Dict[str, Any] = field(default_factory=dict)
    open_dates: Optional[List[str]] = None
    start_date: str = ""
    end_date: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "entity_specified": [e.to_dict() for e in self.entity_specified],
            "entity_shared": {
                key: spec.to_dict() for key, spec in self.entity_shared.items()
            },
            "global": dict(self.global_keys),
            "shm_info": dict(self.shm_info),
            "entities_count": len(self.entity_specified),
            "strategy_info": dict(self.strategy_info),
            "settings": dict(self.settings),
            "output_recorder": dict(self.output_recorder),
        }
        if self.open_dates is not None:
            payload["open_dates"] = list(self.open_dates)
        if self.start_date:
            payload["start_date"] = self.start_date
        if self.end_date:
            payload["end_date"] = self.end_date
        if self.extras:
            payload.update(self.extras)
        return payload


__all__ = ["EntitySpec", "SharedDataSpec", "JobPayloadTemplate"]
