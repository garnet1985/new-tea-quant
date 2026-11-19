"""write_post_process_processor：薄封装 PostProcess.write_user_post_processor_yaml。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.conf.conf import (
    WRITE_POST_PROCESS_PROCESSOR_ALLOWED_FIELDS,
    WRITE_POST_PROCESS_PROCESSOR_MAX_CHARS,
)
from core.modules.post_process import PostProcess


def write_post_process_processor(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if (
        not isinstance(arguments, dict)
        or not set(arguments) <= WRITE_POST_PROCESS_PROCESSOR_ALLOWED_FIELDS
    ):
        return {"ok": False, "error": "只接受参数 key、yaml_body"}
    if "key" not in arguments or "yaml_body" not in arguments:
        return {"ok": False, "error": "必须提供 key、yaml_body"}
    key = arguments.get("key")
    body = arguments.get("yaml_body")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    if not isinstance(body, str) or not body.strip():
        return {"ok": False, "error": "yaml_body 不能为空"}
    if "\x00" in body:
        return {"ok": False, "error": "yaml_body 含有无法写入的字符"}
    if len(body) > WRITE_POST_PROCESS_PROCESSOR_MAX_CHARS:
        return {
            "ok": False,
            "error": f"yaml_body 超过 {WRITE_POST_PROCESS_PROCESSOR_MAX_CHARS} 个字符",
        }
    return PostProcess.write_user_post_processor_yaml(
        key=key.strip(),
        yaml_body=body,
    )
