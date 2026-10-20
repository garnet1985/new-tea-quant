"""write_strategy_files：覆盖已有策略的 strategy.py / settings.py / attribution.py。"""

from __future__ import annotations

import ast
from typing import Any, Dict, List

from core.modules.agent.core.code.conf.conf import (
    WRITE_STRATEGY_ALLOWED_FIELDS,
    WRITE_STRATEGY_MAX_CHARS,
)
from core.modules.agent.core.code.tools.strategy._strategy_key import (
    parse_strategy_key,
    strategy_folder,
)

_CONTRACTS = "from core.modules.strategy.contracts import Records, StrategyContext, StrategyHooks"


def _normalize_strategy(body: str) -> str:
    """模型常编一个不存在的导入。类仍由它写，导入改回契约。"""
    lines = [line for line in body.splitlines() if "import StrategyHooks" not in line]
    if not any(line.strip() == _CONTRACTS for line in lines):
        insert_at = 0
        for index, line in enumerate(lines):
            if line.startswith("from __future__"):
                insert_at = index + 1
        lines.insert(insert_at, _CONTRACTS)
    text = "\n".join(lines).strip() + "\n"
    return text


def _settings_shape_error(body: str) -> str:
    if _dict_from_settings(_python_settings(body)) is None:
        return (
            "settings.py 必须是 Python，以 settings = { 开头。"
            "布尔写 True / False。不要写 YAML。"
            "至少包含 is_enabled、meta.key、data.base。"
            "文件没有被改。"
        )
    return ""


def _attribution_shape_error(body: str) -> str:
    text = _python_settings(body)
    if "attribution" not in text or "{" not in text:
        return "attribution.py 须含 attribution = { ... }。文件没有被改。"
    marker = text.find("attribution")
    start = text.find("{", marker)
    if start < 0:
        return "attribution.py 须含 attribution = { ... }。文件没有被改。"
    try:
        value = ast.literal_eval(text[start:])
    except (SyntaxError, ValueError):
        return "attribution.py 无法解析为字典。文件没有被改。"
    if not isinstance(value, dict):
        return "attribution 必须是字典。文件没有被改。"
    return ""


def _signature_error(body: str) -> str:
    text = str(body or "")
    if "def is_opportunity(self, ctx" in text and "records" in text:
        return ""
    return (
        "is_opportunity 必须写成 def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool。"
        "用 records.last(2)，字段用 dict.get，不要自己构造 Records。文件没有被改。"
    )


def _merge_settings(path, body: str) -> str:
    """保留模板里模型没写到的费用、止盈和组合。布尔从 JSON 改成 Python。"""
    incoming = _python_settings(body)
    new_settings = _dict_from_settings(incoming)
    old_settings = _dict_from_settings(
        path.read_text(encoding="utf-8") if path.is_file() else ""
    )
    if not isinstance(new_settings, dict):
        return incoming
    if not isinstance(old_settings, dict):
        rendered = new_settings
    else:
        rendered = dict(old_settings)
        rendered.update(new_settings)
    if rendered.get("is_enabled") is not True:
        rendered["is_enabled"] = True
    data = rendered.get("data")
    base = data.get("base") if isinstance(data, dict) else None
    if isinstance(base, dict) and base.get("data_key") == "stock.kline.daily":
        simulation = rendered.setdefault("simulation", {})
        if isinstance(simulation, dict):
            execution = simulation.setdefault("execution", {})
            if isinstance(execution, dict):
                execution["mode"] = "entity_based"
        if isinstance(data, dict) and "min_required_records" not in data:
            data["min_required_records"] = 60
    return "settings = " + _literal(rendered) + "\n"


def _dict_from_settings(body: str) -> Dict[str, Any] | None:
    text = str(body or "")
    marker = text.find("settings")
    if marker < 0:
        return None
    start = text.find("{", marker)
    if start < 0:
        return None
    try:
        value = ast.literal_eval(text[start:])
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _literal(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return "None"
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        inner = ", ".join(_literal(item) for item in value)
        return "[" + inner + "]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = [repr(str(key)) + ": " + _literal(item) for key, item in value.items()]
        return "{" + ", ".join(parts) + "}"
    return repr(value)


def _python_settings(body: str) -> str:
    """模型常把 JSON 布尔写进 settings.py。这里改成 Python 字面量。"""
    return (
        body.replace(": true", ": True")
        .replace(": false", ": False")
        .replace(": null", ": None")
    )


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
    folder, relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"策略不存在: {relative}。请先 create_strategy"}

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

    written: List[str] = []
    try:
        if strategy_body:
            strategy_body = _normalize_strategy(strategy_body)
            signature = _signature_error(strategy_body)
            if signature:
                return {"ok": False, "key": parsed, "error": signature}
            (folder / "strategy.py").write_text(strategy_body, encoding="utf-8")
            written.append("strategy.py")
        if settings_body:
            shape = _settings_shape_error(settings_body)
            if shape:
                return {"ok": False, "key": parsed, "error": shape}
            settings_path = folder / "settings.py"
            merged = _merge_settings(settings_path, settings_body)
            settings_path.write_text(merged, encoding="utf-8")
            written.append("settings.py")
        if attribution_body:
            shape = _attribution_shape_error(attribution_body)
            if shape:
                return {"ok": False, "key": parsed, "error": shape}
            text = _python_settings(attribution_body).strip() + "\n"
            (folder / "attribution.py").write_text(text, encoding="utf-8")
            written.append("attribution.py")
    except OSError:
        return {"ok": False, "error": f"无法写入 {relative} 下的策略文件"}

    note = "文件已覆盖。"
    if "strategy.py" in written or "settings.py" in written:
        note += "接着调用 validate_strategy，通过之前不要回测。"
    if "attribution.py" in written:
        note += "归因配置已更新，可重新 start_attribute_*。"
    return {
        "ok": True,
        "key": parsed,
        "path": relative,
        "files": written,
        "note": note.strip(),
    }
