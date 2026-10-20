"""三个策略工具共用的目录名解析。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.conf.agent_policy import resolve_user_write_path
from core.modules.strategy import Strategy

KEY_RULE = "每段以字母开头，仅含字母、数字、下划线"


def parse_strategy_key(
    arguments: Dict[str, Any], *, only: Set[str]
) -> str | Dict[str, Any]:
    """取出合法的策略目录名。参数不对时返回 ``{ok: false, error}``。"""
    if set(arguments) != only:
        names = "、".join(sorted(only))
        return {"ok": False, "error": f"只接受参数 {names}"}
    key = arguments.get("key")
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key 不能为空"}
    key = key.strip().strip("/")
    if not Strategy.is_valid_path(key):
        return {"ok": False, "error": f"目录名不合法：{key}。{KEY_RULE}"}
    return key


def strategy_folder(key: str) -> tuple[Path, str] | Dict[str, Any]:
    """解析 ``strategies/<key>``。

    ``key`` 可以是相对路径，也可以是 ``meta.key``（经 Strategy 发现解析到真实目录）。
    路径不在允许范围时返回错误摘要。
    """
    relative = f"strategies/{key}"
    try:
        folder = resolve_user_write_path(relative)
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
    if folder.is_dir() and (folder / "settings.py").is_file():
        return folder, relative

    # Nested demos: meta.key=rsi_v1 → demo/regression/rsi/rsi_v1_baseline
    try:
        from core.modules.strategy import Strategy

        path_id = str(Strategy.resolve_path(key) or "").strip().strip("/")
    except (FileNotFoundError, ValueError, OSError):
        return folder, relative
    if not path_id or path_id == key:
        return folder, relative
    discovered_rel = f"strategies/{path_id}"
    try:
        discovered = resolve_user_write_path(discovered_rel)
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
    return discovered, discovered_rel
