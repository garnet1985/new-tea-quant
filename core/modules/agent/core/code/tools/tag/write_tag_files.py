"""write_tag_files：覆盖已有标签的 tag.py / settings.py。"""

from __future__ import annotations

import ast
from typing import Any, Dict, List

from core.modules.agent.core.code.conf.conf import (
    WRITE_TAG_ALLOWED_FIELDS,
    WRITE_TAG_MAX_CHARS,
)
from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder

_CONTRACTS = "from core.modules.tag.contracts import TagCalendarAsOfResult, TagContext, TagHooks"


def _normalize_tag(body: str) -> str:
    """模型常编一个不存在的导入。类仍由它写，导入改回契约。"""
    lines = [
        line
        for line in body.splitlines()
        if "import TagHooks" not in line or "core.modules.tag" in line
    ]
    # Drop broken single-name imports that aren't from contracts.
    cleaned: List[str] = []
    for line in lines:
        if line.strip() in {
            "from core.modules.tag import TagHooks",
            "from core.modules.tag.core.engines.shared.hooks import TagHooks",
        }:
            continue
        cleaned.append(line)
    lines = cleaned
    if not any("from core.modules.tag.contracts import" in line for line in lines):
        insert_at = 0
        for index, line in enumerate(lines):
            if line.startswith("from __future__"):
                insert_at = index + 1
        lines.insert(insert_at, _CONTRACTS)
    return "\n".join(lines).strip() + "\n"


def _settings_shape_error(body: str) -> str:
    if _dict_from_settings(_python_settings(body)) is None:
        return (
            "settings.py 必须是 Python，以 settings = { 开头。"
            "布尔写 True / False。不要写 YAML。"
            "至少包含 is_enabled、meta.key、data.base、tag_definitions。"
            "文件没有被改。"
        )
    return ""


def _signature_error(body: str) -> str:
    text = str(body or "")
    if "def calculate_tag(self, ctx" in text:
        return ""
    return (
        "calculate_tag 必须写成 def calculate_tag(self, ctx: TagContext) -> dict | None。"
        "返回 {\"value\": ...} 或 None。文件没有被改。"
    )


def _merge_settings(path, body: str) -> str:
    """保留模板里模型没写到的块；补上 Tag 默认值。"""
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
    if isinstance(data, dict) and "min_required_records" not in data:
        data["min_required_records"] = 0
    calculation = rendered.setdefault("calculation", {})
    if isinstance(calculation, dict):
        calculation.setdefault("update_mode", "incremental")
        calculation.setdefault("recompute", False)
        execution = calculation.setdefault("execution", {})
        if isinstance(execution, dict):
            base = data.get("base") if isinstance(data, dict) else None
            data_key = ""
            if isinstance(base, dict):
                data_key = str(base.get("data_key") or "")
            if data_key == "stock.kline.daily":
                execution.setdefault("mode", "entity_based")
            execution.setdefault("start_date", "")
            execution.setdefault("end_date", "")
    if not isinstance(rendered.get("tag_definitions"), list):
        rendered["tag_definitions"] = []
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
    if len(body) > WRITE_TAG_MAX_CHARS:
        return {
            "ok": False,
            "error": f"{name} 超过 {WRITE_TAG_MAX_CHARS} 个字符",
        }
    return body


def write_tag_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """覆盖 tag.py / settings.py（至少写一个）。目录须已存在。"""
    if not isinstance(arguments, dict) or not set(arguments) <= WRITE_TAG_ALLOWED_FIELDS:
        return {
            "ok": False,
            "error": "只接受参数 key、tag_py、settings_py",
        }
    if "key" not in arguments:
        return {"ok": False, "error": "必须提供 key"}
    parsed = parse_tag_key({"key": arguments.get("key")}, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located
    folder, relative = located
    if not folder.is_dir():
        return {"ok": False, "error": f"标签不存在: {relative}。请先 create_tag"}

    tag_body = _read_body(arguments, "tag_py")
    if isinstance(tag_body, dict):
        return tag_body
    settings_body = _read_body(arguments, "settings_py")
    if isinstance(settings_body, dict):
        return settings_body
    if not tag_body and not settings_body:
        return {
            "ok": False,
            "error": "至少提供 tag_py、settings_py 之一",
        }

    written: List[str] = []
    try:
        if tag_body:
            tag_body = _normalize_tag(tag_body)
            signature = _signature_error(tag_body)
            if signature:
                return {"ok": False, "key": parsed, "error": signature}
            (folder / "tag.py").write_text(tag_body, encoding="utf-8")
            written.append("tag.py")
        if settings_body:
            shape = _settings_shape_error(settings_body)
            if shape:
                return {"ok": False, "key": parsed, "error": shape}
            settings_path = folder / "settings.py"
            merged = _merge_settings(settings_path, settings_body)
            settings_path.write_text(merged, encoding="utf-8")
            written.append("settings.py")
    except OSError:
        return {"ok": False, "error": f"无法写入 {relative} 下的标签文件"}

    return {
        "ok": True,
        "key": parsed,
        "path": relative,
        "files": written,
        "note": "文件已覆盖。接着调用 validate_tag，通过之前不要跑打标。",
    }
