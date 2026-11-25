"""跨模块契约：AI 通道供应商快照与调用错误。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


class AiError(Exception):
    """AI 通道配置或调用失败。"""


@dataclass(frozen=True)
class CompleteResult:
    """一次补全的回复。不含密钥。"""

    reply: str
    provider_id: str
    model: str
    ntq: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ProviderInfo:
    """userspace 供应商目录的只读快照（不含密钥明文）。"""

    provider_id: str
    directory: Path
    base_url: str
    model: str
    enabled: bool
    has_api_key: bool


__all__ = ["AiError", "CompleteResult", "ProviderInfo"]
