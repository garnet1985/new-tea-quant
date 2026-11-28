"""进度树共用小工具（id 清洗、最深匹配节点）。"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional, Set, Union


def safe_progress_id(raw: str) -> str:
    """去掉路径分隔与空字符，供根/子节点 id 与文件名片段使用。"""
    return (
        str(raw or "")
        .replace("/", "-")
        .replace("\\", "-")
        .replace("\x00", "")
        .strip()
    )


def child_progress_id(root: str, name: str) -> str:
    """``{root}:{safe_name}``。"""
    return f"{root}:{safe_progress_id(name)}"


StatusSet = Union[FrozenSet[str], Set[str]]


def deepest_matching(
    node: Dict[str, Any], statuses: StatusSet
) -> Optional[Dict[str, Any]]:
    """深度优先：返回树中 status 落在 ``statuses`` 的最深节点（并列取后写覆盖）。"""
    found: Optional[Dict[str, Any]] = (
        node if str(node.get("status") or "") in statuses else None
    )
    for child in node.get("steps") or []:
        if not isinstance(child, dict):
            continue
        deeper = deepest_matching(child, statuses)
        if deeper is not None:
            found = deeper
    return found
