"""只读探查：薄封装 PostProcess list/describe。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.post_process import PostProcess


def list_post_process_adapters(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    _ = arguments
    return PostProcess.list_user_adapter_summaries()


def list_post_process_processors(
    arguments: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    _ = arguments
    return PostProcess.list_user_post_processor_summaries()


def describe_post_process_adapter(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"name"}:
        return {"ok": False, "error": "只接受参数 name"}
    name = arguments.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "error": "name 不能为空"}
    return PostProcess.describe_user_adapter(name=name.strip())


def describe_post_process_processor(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(arguments, dict) or set(arguments) != {"key"}:
        return {"ok": False, "error": "只接受参数 key"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    return PostProcess.describe_user_post_processor(key=key.strip())
