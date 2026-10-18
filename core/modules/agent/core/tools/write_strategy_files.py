"""write_strategy_files：覆盖已有策略的两个文件。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.tools._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)

_MAX_CHARS = 200_000


def write_strategy_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """只覆盖 strategy.py 与 settings.py。目录必须已经存在。"""
    parsed = parse_strategy_key(arguments, only={"key", "strategy_py", "settings_py"})
    if isinstance(parsed, dict):
        return parsed
    located = strategy_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"策略不存在: {relative}。请先 create_strategy"}

    texts: Dict[str, str] = {}
    for name in ("strategy_py", "settings_py"):
        body = arguments.get(name)
        if not isinstance(body, str) or not body.strip():
            return {"ok": False, "error": f"{name} 不能为空"}
        if "\x00" in body:
            return {"ok": False, "error": f"{name} 含有无法写入的字符"}
        if len(body) > _MAX_CHARS:
            return {"ok": False, "error": f"{name} 超过 {_MAX_CHARS} 个字符"}
        texts[name] = body

    strategy_file = folder / "strategy.py"
    settings_file = folder / "settings.py"
    try:
        strategy_file.write_text(texts["strategy_py"], encoding="utf-8")
        settings_file.write_text(texts["settings_py"], encoding="utf-8")
    except OSError:
        return {"ok": False, "error": f"无法写入 {relative} 下的策略文件"}
    return {
        "ok": True,
        "key": parsed,
        "path": relative,
        "files": ["strategy.py", "settings.py"],
        "note": "文件已覆盖。接着调用 validate_strategy，通过之前不要回测",
    }
