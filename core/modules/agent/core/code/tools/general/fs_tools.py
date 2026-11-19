"""userspace 只读：列目录、搜文件内容、读文件。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.conf.agent_policy import resolve_user_read_path
from core.modules.agent.core.code.conf.conf import (
    READ_FILE_MAX_CHARS,
    SEARCH_FILES_MAX_HITS,
    SEARCH_FILES_MAX_LINE_CHARS,
)

_TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".csv",
        ".ini",
        ".cfg",
    }
)


def list_dir(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """列出 userspace 下某相对目录的一层条目。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"path"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    rel = args.get("path", "strategies")
    if not isinstance(rel, str):
        return {"ok": False, "error": "path 须为字符串"}
    rel = rel.strip().strip("/") or "strategies"
    try:
        folder = resolve_user_read_path(rel)
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
    if not folder.is_dir():
        return {"ok": False, "error": f"目录不存在: {rel}"}
    entries: List[Dict[str, Any]] = []
    try:
        children = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError as exc:
        return {"ok": False, "error": f"无法列出目录: {exc}"}
    for child in children[:200]:
        name = child.name
        if name.startswith(".") or name == "__pycache__":
            continue
        kind = "dir" if child.is_dir() else "file"
        entries.append({"name": name, "kind": kind, "path": f"{rel}/{name}"})
    return {
        "ok": True,
        "path": rel,
        "entries": entries,
        "count": len(entries),
        "note": "只读一层。接着可用 read_file 或 search_files。",
    }


def search_files(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """在允许的 userspace 树内按子串搜文件内容（默认 *.py）。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"query", "path", "glob"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "query 不能为空"}
    query = query.strip()
    if len(query) > 120:
        return {"ok": False, "error": "query 最多 120 个字符"}
    root_rel = args.get("path") or "strategies"
    if not isinstance(root_rel, str) or not root_rel.strip():
        return {"ok": False, "error": "path 须为非空字符串"}
    root_rel = root_rel.strip().strip("/")
    glob_pat = args.get("glob") or "*.py"
    if not isinstance(glob_pat, str) or not glob_pat.strip():
        return {"ok": False, "error": "glob 须为字符串"}
    glob_pat = glob_pat.strip()
    try:
        root = resolve_user_read_path(root_rel)
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
    if not root.is_dir():
        return {"ok": False, "error": f"目录不存在: {root_rel}"}

    hits: List[Dict[str, Any]] = []
    truncated = False
    try:
        candidates = sorted(root.rglob(glob_pat))
    except OSError as exc:
        return {"ok": False, "error": f"搜索失败: {exc}"}
    for path in candidates:
        if not path.is_file():
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES and glob_pat == "*.py":
            continue
        if any(part in {"__pycache__", ".git"} for part in path.parts):
            continue
        try:
            resolve_user_read_path(_rel_under_userspace(path))
        except AgentError:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if query not in line:
                continue
            rel = _rel_under_userspace(path)
            snippet = line.strip()
            if len(snippet) > SEARCH_FILES_MAX_LINE_CHARS:
                snippet = snippet[: SEARCH_FILES_MAX_LINE_CHARS] + "…"
            hits.append({"path": rel, "line": i, "text": snippet})
            if len(hits) >= SEARCH_FILES_MAX_HITS:
                truncated = True
                break
        if truncated:
            break
    return {
        "ok": True,
        "query": query,
        "path": root_rel,
        "glob": glob_pat,
        "hits": hits,
        "count": len(hits),
        "truncated": truncated,
        "note": "只读匹配行。改文件前先 read_file 看全文上下文。",
    }


def read_file(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """读取 userspace 内允许的文本文件。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"path", "max_chars", "start_line"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}
    rel = args.get("path")
    if not isinstance(rel, str) or not rel.strip():
        return {"ok": False, "error": "path 不能为空"}
    rel = rel.strip().strip("/")
    max_chars = args.get("max_chars", READ_FILE_MAX_CHARS)
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        return {"ok": False, "error": "max_chars 须为正整数"}
    max_chars = min(max_chars, READ_FILE_MAX_CHARS)
    start_line = args.get("start_line", 1)
    if isinstance(start_line, bool) or not isinstance(start_line, int) or start_line < 1:
        return {"ok": False, "error": "start_line 须为正整数"}
    try:
        path = resolve_user_read_path(rel)
    except AgentError as exc:
        return {"ok": False, "error": str(exc)}
    if not path.is_file():
        return {"ok": False, "error": f"文件不存在: {rel}"}
    if path.suffix.lower() not in _TEXT_SUFFIXES and path.suffix:
        return {"ok": False, "error": f"不支持的文件类型: {path.suffix}"}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "error": f"无法读取: {exc}"}
    lines = text.splitlines(keepends=True)
    if start_line > len(lines) and lines:
        return {"ok": False, "error": f"start_line 超出文件行数 ({len(lines)})"}
    sliced = "".join(lines[start_line - 1 :]) if lines else text
    truncated = len(sliced) > max_chars
    body = sliced[:max_chars]
    return {
        "ok": True,
        "path": rel,
        "start_line": start_line,
        "total_lines": len(lines),
        "chars": len(body),
        "truncated": truncated,
        "content": body,
        "note": "只读。要改策略/标签请用对应 write_* 工具整文件覆盖。",
    }


def _rel_under_userspace(path: Path) -> str:
    from core.infra.project_context import ProjectContext

    root = ProjectContext.path.get_userspace_root().resolve()
    resolved = path.resolve()
    return resolved.relative_to(root).as_posix()
