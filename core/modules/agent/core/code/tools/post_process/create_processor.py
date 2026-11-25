"""create_post_process_processor：薄封装 PostProcess.scaffold_user_post_processor。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.post_process import PostProcess


def create_post_process_processor(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    key = args.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    name = args.get("name", "")
    if name is None:
        name = ""
    if not isinstance(name, str):
        return {"ok": False, "error": "name 须为字符串"}
    adapter_name = args.get("adapter_name", "")
    if adapter_name is None:
        adapter_name = ""
    if not isinstance(adapter_name, str):
        return {"ok": False, "error": "adapter_name 须为字符串"}
    is_enabled = args.get("is_enabled", False)
    if not isinstance(is_enabled, bool):
        return {"ok": False, "error": "is_enabled 须为布尔"}
    extra = set(args) - {"key", "name", "adapter_name", "is_enabled"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    return PostProcess.scaffold_user_post_processor(
        key=key.strip(),
        name=name.strip(),
        adapter_name=adapter_name.strip(),
        is_enabled=is_enabled,
    )
