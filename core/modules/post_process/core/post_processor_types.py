"""PostProcessor 声明的内存形态（由 YAML 加载）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AdapterBinding:
    """PostProcessor 内对某个 adapter 的声明。"""

    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class PostProcessorDefinition:
    """一份后续处理声明（post_processors/<key>）。"""

    key: str
    name: str = ""
    is_enabled: bool = True
    on_error: str = "continue"  # continue | stop
    on_empty: str = "run"  # run | skip
    adapters: Dict[str, AdapterBinding] = field(default_factory=dict)


__all__ = ["AdapterBinding", "PostProcessorDefinition"]
