"""validate_tag：薄封装 Tag.validate_artifact。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.agent.core.code.tools.tag._tag_key import parse_tag_key, tag_folder
from core.modules.tag import Tag


def validate_tag(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """加载已写好的标签。失败时返回错误列表，不启动打标。"""
    parsed = parse_tag_key(arguments, only={"key"})
    if isinstance(parsed, dict):
        return parsed
    located = tag_folder(parsed)
    if isinstance(located, dict):
        return located
    return Tag.validate_artifact(key=parsed)
