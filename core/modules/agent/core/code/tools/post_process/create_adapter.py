"""create_post_process_adapter：薄封装 PostProcess.scaffold_user_adapter。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.post_process import PostProcess


def create_post_process_adapter(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments or {})
    name = args.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "error": "name 不能为空"}
    display_name = args.get("display_name", "")
    if display_name is None:
        display_name = ""
    if not isinstance(display_name, str):
        return {"ok": False, "error": "display_name 须为字符串"}
    extra = set(args) - {"name", "display_name"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    return PostProcess.scaffold_user_adapter(
        name=name.strip(),
        display_name=display_name.strip(),
    )
