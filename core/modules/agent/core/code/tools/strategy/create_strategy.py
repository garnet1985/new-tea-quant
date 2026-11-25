"""create_strategy：薄封装 Strategy.scaffold_from_template。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.tools.strategy._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)
from core.modules.strategy import Strategy


def create_strategy(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """新建策略。参数校验在信道；建目录与 meta.key 对齐在 Facade。"""
    parsed = parse_strategy_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    _dest, relative = located
    out = Strategy.scaffold_from_template(parsed)
    if not out.get("ok"):
        return {"ok": False, "error": _short_create_error(str(out.get("error") or ""), relative)}
    return {
        "ok": True,
        "key": out.get("key") or parsed,
        "path": out.get("path") or relative,
        "files": list(out.get("files") or ["strategy.py", "settings.py"]),
        "note": str(out.get("note") or ""),
    }


def _short_create_error(message: str, relative: str) -> str:
    text = message.strip()
    if text.startswith("目标已存在"):
        return f"目标已存在: {relative}"
    if "模板目录不存在" in text or "策略模板不存在" in text:
        return "策略模板不存在: strategies/_template/empty_strategy"
    return text
