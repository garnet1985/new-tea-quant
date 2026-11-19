"""Tag 工具共用的目录名解析（只经 Tag Facade）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.conf.agent_policy import resolve_user_write_path
from core.modules.tag import Tag

KEY_RULE = "每段以字母开头，仅含字母、数字、下划线"


def parse_tag_key(
    arguments: Dict[str, Any], *, only: Set[str]
) -> str | Dict[str, Any]:
    """取出合法的标签相对路径。参数不对时返回 ``{ok: false, error}``。"""
    if set(arguments) != only:
        names = "、".join(sorted(only))
        return {"ok": False, "error": f"只接受参数 {names}"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    key = key.strip().strip("/")
    if not Tag.is_valid_path(key):
        return {"ok": False, "error": f"目录名不合法：{key}。{KEY_RULE}"}
    return key


def tag_folder(key: str) -> tuple[Path, str] | Dict[str, Any]:
    """解析 ``extensions/tags/<key>``（认 path 或 ``meta.key``）。"""
    relative = f"extensions/tags/{key}"
    try:
        folder = resolve_user_write_path(relative)
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
    if folder.is_dir() and (folder / "settings.py").is_file():
        return folder, relative

    try:
        path_id = Tag.resolve_path(key)
    except FileNotFoundError:
        return folder, relative
    if not path_id or path_id == key:
        return folder, relative
    discovered_rel = f"extensions/tags/{path_id}"
    try:
        discovered = resolve_user_write_path(discovered_rel)
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
    return discovered, discovered_rel
