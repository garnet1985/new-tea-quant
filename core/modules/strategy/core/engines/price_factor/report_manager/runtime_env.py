"""价格回测 ``runtime_env.json`` 与 entity_ids 落盘。

本文件:
- PriceRuntimeEnv: runtime 字段序列化 / write_entity_ids
  边界: 负责 runtime 文件内容；不负责 overall 汇总或 worker CSV
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.system import get_version


@dataclass
class PriceRuntimeEnv:
    """价格回测 version 的 ``runtime_env.json``。"""

    strategy_key: str
    strategy_path: str
    version_id: int
    enum_version_id: str
    enum_output_dir: str
    settings_fp: str
    env_fp: str
    period: Dict[str, str] = field(default_factory=dict)
    entity_ids: List[str] = field(default_factory=list)
    market_profile: str = ""
    engine_version: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "version_id": int(self.version_id),
            "enum_version_id": self.enum_version_id,
            "enum_output_dir": self.enum_output_dir,
            "settings_fp": self.settings_fp,
            "env_fp": self.env_fp,
            "period": dict(self.period or {}),
            "entity_ids": list(self.entity_ids or []),
            "entity_count": len(self.entity_ids or []),
            "market_profile": self.market_profile,
            "engine_version": self.engine_version or get_version(),
            "created_at": self.created_at or datetime.now().isoformat(),
            "kind": "price_factor",
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "PriceRuntimeEnv":
        data = raw or {}
        period = data.get("period") if isinstance(data.get("period"), dict) else {}
        entity_ids = data.get("entity_ids")
        if not isinstance(entity_ids, list):
            entity_ids = []
        return cls(
            strategy_key=str(data.get("strategy_key") or "").strip(),
            strategy_path=str(data.get("strategy_path") or "").strip(),
            version_id=int(data.get("version_id") or 0),
            enum_version_id=str(data.get("enum_version_id") or "").strip(),
            enum_output_dir=str(data.get("enum_output_dir") or "").strip(),
            settings_fp=str(data.get("settings_fp") or "").strip(),
            env_fp=str(data.get("env_fp") or "").strip(),
            period={
                "start_date": str(period.get("start_date") or "").strip(),
                "end_date": str(period.get("end_date") or "").strip(),
            },
            entity_ids=[str(x).strip() for x in entity_ids if str(x).strip()],
            market_profile=str(data.get("market_profile") or "").strip(),
            engine_version=str(data.get("engine_version") or "").strip(),
            created_at=str(data.get("created_at") or "").strip(),
        )

    def save(self, output_dir: Path) -> Path:
        store = ArtifactStore.at(output_dir, kind=SimulateKind.PRICE_FACTOR)
        path = store.write_json("runtime_env", self.to_dict())
        store.write_text_lines("entity_ids", self.entity_ids)
        return path

    @classmethod
    def load(cls, output_dir: Path) -> "PriceRuntimeEnv":
        store = ArtifactStore.at(output_dir, kind=SimulateKind.PRICE_FACTOR)
        env = cls.from_dict(store.read_json("runtime_env"))
        lines = store.read_text_lines("entity_ids")
        if lines:
            env.entity_ids = lines
        return env


__all__ = ["PriceRuntimeEnv"]
