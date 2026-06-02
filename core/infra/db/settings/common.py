"""
跨 backend 公用配置（来自 merged config 顶层 batch_write）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class BatchWriteSettings:
    enable: bool = True
    batch_size: int = 1000
    flush_interval: float = 5.0
    insert_batch_size: int = 5000

    def as_dict(self) -> Dict[str, Any]:
        return {
            "enable": self.enable,
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval,
            "_advanced": {"insert_batch_size": self.insert_batch_size},
        }


def parse_batch_write(raw: Dict[str, Any] | None) -> BatchWriteSettings:
    data = dict(raw or {})
    advanced = data.get("_advanced") or {}
    if not isinstance(advanced, dict):
        advanced = {}
    return BatchWriteSettings(
        enable=bool(data.get("enable", True)),
        batch_size=int(data.get("batch_size", 1000)),
        flush_interval=float(data.get("flush_interval", 5.0)),
        insert_batch_size=int(advanced.get("insert_batch_size", 5000)),
    )
