"""write_post_process_adapter_files：薄封装 PostProcess.write_user_adapter_files。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_POST_PROCESS_ADAPTER_ALLOWED_FIELDS,
    WRITE_POST_PROCESS_ADAPTER_MAX_CHARS,
)
from core.modules.post_process import PostProcess


def write_post_process_adapter_files(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if (
        not isinstance(arguments, dict)
        or not set(arguments) <= WRITE_POST_PROCESS_ADAPTER_ALLOWED_FIELDS
    ):
        return {"ok": False, "error": "只接受参数 name、adapter_py、settings_py"}
    if "name" not in arguments:
        return {"ok": False, "error": "必须提供 name"}
    name = arguments.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "error": "name 不能为空"}

    adapter_py = _body(arguments, "adapter_py")
    if isinstance(adapter_py, dict):
        return adapter_py
    settings_py = _body(arguments, "settings_py")
    if isinstance(settings_py, dict):
        return settings_py
    return PostProcess.write_user_adapter_files(
        name=name.strip(),
        adapter_py=adapter_py,
        settings_py=settings_py,
    )


def _body(arguments: Dict[str, Any], name: str) -> str | Dict[str, Any]:
    body = arguments.get(name)
    if body is None:
        return ""
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": f"{name} 不能为空字符串"}
    if "\x00" in body:
        return {"ok": False, "error": f"{name} 含有无法写入的字符"}
    if len(body) > WRITE_POST_PROCESS_ADAPTER_MAX_CHARS:
        return {
            "ok": False,
            "error": f"{name} 超过 {WRITE_POST_PROCESS_ADAPTER_MAX_CHARS} 个字符",
        }
    return body
