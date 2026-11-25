"""validate_post_process_adapter：薄封装 PostProcess.validate_user_adapter。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.post_process import PostProcess


def validate_post_process_adapter(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"name"}:
        return {"ok": False, "error": "只接受参数 name"}
    name = arguments.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "error": "name 不能为空"}
    return PostProcess.validate_user_adapter(name=name.strip())
