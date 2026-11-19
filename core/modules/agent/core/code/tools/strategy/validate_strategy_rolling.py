"""validate_strategy_rolling：薄封装 Strategy.validate_user_rolling。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.tools.strategy._strategy_key import parse_strategy_key
from core.modules.strategy import Strategy


def validate_strategy_rolling(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"key"}:
        return {"ok": False, "error": "只接受参数 key"}
    parsed = parse_strategy_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    return Strategy.validate_user_rolling(key=parsed)
