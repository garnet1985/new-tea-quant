"""已发现的序列关系场景。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class DiscoveredRelation:
    """磁盘上通过校验的 series_relation 场景。"""

    key: str
    display_name: str
    relative_path: str
    folder: Path
    settings: Dict[str, Any]

    def id(self) -> str:
        return self.relative_path


__all__ = ["DiscoveredRelation"]
