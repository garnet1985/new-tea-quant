"""lookup_framework_index：框架「怎么算 / 在哪」快速索引（远端优先，本地兜底）。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.agent.core.code.tools.general.framework_index_lib import (
    load_local_entries,
    match_entries,
    normalize_remote_entries,
)


def lookup_framework_index(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """按问题匹配框架索引条目；优先官网可运营索引，失败则用本机 wiki 副本。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"query", "limit"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "query 不能为空"}
    query = query.strip()
    if len(query) > 120:
        return {"ok": False, "error": "query 最多 120 个字符"}

    limit = 5
    if args.get("limit") is not None:
        try:
            limit = int(args["limit"])
        except (TypeError, ValueError):
            return {"ok": False, "error": "limit 须为整数"}

    source = "local"
    version = None
    entries: List[Dict[str, Any]] = []
    remote_note = None

    remote = _try_remote()
    if remote and remote.get("ok"):
        entries = normalize_remote_entries(remote.get("entries"))
        if entries:
            source = "remote"
            version = remote.get("version")
        else:
            remote_note = "远端索引为空，已改用本地"
    elif remote and remote.get("error"):
        remote_note = str(remote.get("error"))

    if not entries:
        entries = load_local_entries()
        source = "local"

    if not entries:
        return {
            "ok": False,
            "error": "框架索引不可用（本地 framework_index.md 缺失）",
            "source": source,
        }

    hits = match_entries(query, entries, limit=limit)
    out: Dict[str, Any] = {
        "ok": True,
        "query": query,
        "source": source,
        "version": version,
        "hits": hits,
        "count": len(hits),
        "note": (
            "框架「怎么算 / 在哪实现」导航。命中后用 search_wiki 打开 wiki 字段；"
            "需要源码细节再 read_file code 路径。详细说明书仍以 ntq_wiki 为准。"
        ),
    }
    if remote_note and source == "local":
        out["fallback_from_remote"] = remote_note
    return out


def _try_remote() -> Dict[str, Any] | None:
    """有会员凭证时尝试拉官网索引；无凭证或导入失败返回 None。"""
    try:
        from core.modules.ntq_external.ai.framework_index import fetch_framework_index
    except Exception:
        return None
    try:
        return fetch_framework_index()
    except Exception as exc:  # noqa: BLE001 — tool must not crash the agent
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
