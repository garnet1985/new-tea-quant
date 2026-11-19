"""write_strategy_rolling：薄封装 Strategy.write_user_rolling。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_STRATEGY_MAX_CHARS,
    WRITE_STRATEGY_ROLLING_ALLOWED_FIELDS,
)
from core.modules.agent.core.code.tools.strategy._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)
from core.modules.strategy import Strategy


def write_strategy_rolling(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if (
        not isinstance(arguments, dict)
        or not set(arguments) <= WRITE_STRATEGY_ROLLING_ALLOWED_FIELDS
    ):
        return {"ok": False, "error": "只接受参数 key、rolling_py"}
    if "key" not in arguments or "rolling_py" not in arguments:
        return {"ok": False, "error": "必须提供 key、rolling_py"}
    parsed = parse_strategy_key({"key": arguments.get("key")}, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    body = arguments.get("rolling_py")
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": "rolling_py 不能为空"}
    if "\x00" in body:
        return {"ok": False, "error": "rolling_py 含有无法写入的字符"}
    if len(body) > WRITE_STRATEGY_MAX_CHARS:
        return {
            "ok": False,
            "error": f"rolling_py 超过 {WRITE_STRATEGY_MAX_CHARS} 个字符",
        }
    out = Strategy.write_user_rolling(key=parsed, rolling_py=body)
    if not out.get("ok"):
        err = str(out.get("error") or "写入失败").replace(
            "scaffold_from_template", "create_strategy"
        )
        payload = {"ok": False, "error": err}
        if "key" in out:
            payload["key"] = out["key"]
        return payload
    return {
        "ok": True,
        "key": out.get("key") or parsed,
        "path": out.get("path") or located[1],
        "files": list(out.get("files") or ["rolling.py"]),
        "note": "rolling.py 已覆盖。接着 validate_strategy_rolling，通过后再 start_rolling。",
    }
