"""validate_strategy：薄封装 Strategy.validate_artifact。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.tools.strategy._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)
from core.modules.strategy import Strategy


def validate_strategy(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """加载已写好的策略。失败时返回错误列表，不启动回测。"""
    parsed = parse_strategy_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    return Strategy.validate_artifact(key=parsed)
