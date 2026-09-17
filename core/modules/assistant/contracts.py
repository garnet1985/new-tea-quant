"""跨模块契约：助理供应商发现结果。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProviderInfo:
    """userspace 供应商目录的只读快照（不含密钥明文）。"""

    provider_id: str
    directory: Path
    base_url: str
    model: str
    enabled: bool
    has_api_key: bool


__all__ = ["ProviderInfo"]
