"""write_strategy_files：薄封装 Strategy.apply_settings_patch。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_STRATEGY_ALLOWED_FIELDS,
    WRITE_STRATEGY_MAX_CHARS,
)
from core.modules.agent.core.code.tools.strategy._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)
from core.modules.strategy import Strategy


def _read_body(arguments: Dict[str, Any], name: str) -> str | Dict[str, Any]:
    body = arguments.get(name)
    if body is None:
        return ""
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": f"{name} 不能为空字符串"}
    if "\x00" in body:
        return {"ok": False, "error": f"{name} 含有无法写入的字符"}
    if len(body) > WRITE_STRATEGY_MAX_CHARS:
        return {
            "ok": False,
            "error": f"{name} 超过 {WRITE_STRATEGY_MAX_CHARS} 个字符",
        }
    return body


def write_strategy_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """覆盖 strategy.py / settings.py / attribution.py（至少写一个）。目录须已存在。"""
    if not isinstance(arguments, dict) or not set(arguments) <= WRITE_STRATEGY_ALLOWED_FIELDS:
        return {
            "ok": False,
            "error": "只接受参数 key、strategy_py、settings_py、attribution_py",
        }
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    parsed = parse_strategy_key({"key": arguments.get("key")}, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located

    strategy_body = _read_body(arguments, "strategy_py")
    if isinstance(strategy_body, dict):
        return strategy_body
    settings_body = _read_body(arguments, "settings_py")
    if isinstance(settings_body, dict):
        return settings_body
    attribution_body = _read_body(arguments, "attribution_py")
    if isinstance(attribution_body, dict):
        return attribution_body
    if not strategy_body and not settings_body and not attribution_body:
        return {
            "ok": False,
            "error": "至少提供 strategy_py、settings_py、attribution_py 之一",
        }

    out = Strategy.apply_settings_patch(
        key=parsed,
        strategy_py=strategy_body,
        settings_py=settings_body,
        attribution_py=attribution_body,
    )
    if not out.get("ok"):
        err = str(out.get("error") or "写入失败")
        err = err.replace("scaffold_from_template", "create_strategy")
        payload = {"ok": False, "error": err}
        if "key" in out:
            payload["key"] = out["key"]
        return payload

    written = list(out.get("files") or [])
    note = "文件已覆盖。"
    if "strategy.py" in written or "settings.py" in written:
        note += "接着调用 validate_strategy，通过之前不要回测。"
    if "attribution.py" in written:
        note += "归因配置已更新，可重新 start_attribute_*。"
    return {
        "ok": True,
        "key": out.get("key") or parsed,
        "path": out.get("path") or located[1],
        "files": written,
        "note": note.strip(),
    }
