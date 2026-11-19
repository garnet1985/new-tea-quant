"""search_wiki：在 ntq_wiki 内按子串检索说明书。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.modules.agent.core.code.conf.conf import (
    SEARCH_FILES_MAX_HITS,
    SEARCH_FILES_MAX_LINE_CHARS,
)

_WIKI_ROOT = (
    Path(__file__).resolve().parents[3] / "content" / "ntq_wiki"
)


def search_wiki(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """搜索产品 wiki（know_how / wiki 等 Markdown）。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"query"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "query 不能为空"}
    query = query.strip()
    if len(query) > 120:
        return {"ok": False, "error": "query 最多 120 个字符"}

    root = _WIKI_ROOT.resolve()
    if not root.is_dir():
        return {"ok": False, "error": "wiki 目录不可用"}

    hits: List[Dict[str, Any]] = []
    truncated = False
    for path in sorted(root.rglob("*.md")):
        try:
            path.relative_to(root)
        except ValueError:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                text = text[end + 4 :].lstrip("\n")
        rel = path.relative_to(root).as_posix()
        for i, line in enumerate(text.splitlines(), start=1):
            if query not in line and query.lower() not in line.lower():
                continue
            snippet = line.strip()
            if len(snippet) > SEARCH_FILES_MAX_LINE_CHARS:
                snippet = snippet[:SEARCH_FILES_MAX_LINE_CHARS] + "…"
            hits.append({"path": rel, "line": i, "text": snippet})
            if len(hits) >= SEARCH_FILES_MAX_HITS:
                truncated = True
                break
        if truncated:
            break
    return {
        "ok": True,
        "query": query,
        "hits": hits,
        "count": len(hits),
        "truncated": truncated,
        "note": "产品说明书检索。外网新闻请用 web_search。",
    }
