"""跨模块契约：工具清单与 agent 错误。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class AgentError(Exception):
    """工具参数不合法，或运行循环尚不能继续。消息中不得包含 api_key。"""


@dataclass(frozen=True)
class ToolSpec:
    """登记给模型的一个工具。不含可执行体。"""

    name: str
    description: str
    parameters: Dict[str, Any]
    implemented: bool


__all__ = ["AgentError", "ToolSpec"]
