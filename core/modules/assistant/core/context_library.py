"""从 ``context/global|wiki|know_how`` 发现 markdown 百科。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

import yaml

_CONTEXT_ROOT = Path(__file__).resolve().parents[1] / "context"
_KIND_DIRS = ("global", "wiki", "know_how")
_SKIP_NAMES = frozenset({"readme.md"})
_MAX_PICK = 3
_MAX_CHARS = 32000
_PICKED_RESERVE = 12000
_ATTACH_ALL_IF_FEWER_THAN = 2


@dataclass(frozen=True)
class ContextDoc:
    """一篇百科：``doc_id`` 形如 ``know_how/config_strategy_settings``。"""

    doc_id: str
    kind: str
    title: str
    aliases: tuple
    summary: str
    body: str


def list_context_docs() -> List[ContextDoc]:
    """扫描三个分类目录下的 ``*.md``（不含 README）。"""
    if not _CONTEXT_ROOT.is_dir():
        return []
    docs: List[ContextDoc] = []
    for kind in _KIND_DIRS:
        folder = _CONTEXT_ROOT / kind
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*.md")):
            if path.name.lower() in _SKIP_NAMES:
                continue
            rel = path.relative_to(folder).with_suffix("")
            doc_id = f"{kind}/{rel.as_posix()}"
            meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
            body = str(body or "").strip()
            title = str(meta.get("title") or "").strip() or _heading_title(body) or path.stem
            aliases = _string_tuple(meta.get("aliases"))
            summary = str(meta.get("summary") or "").strip()
            docs.append(
                ContextDoc(
                    doc_id=doc_id,
                    kind=kind,
                    title=title,
                    aliases=aliases,
                    summary=summary,
                    body=body,
                )
            )
    return docs


def docs_of_kind(docs: Sequence[ContextDoc], kind: str) -> List[ContextDoc]:
    return [item for item in docs if item.kind == kind]


def catalog_text(docs: Sequence[ContextDoc]) -> str:
    """给模型看的短目录（不含正文）。"""
    lines: List[str] = []
    for item in docs:
        alias = "、".join(item.aliases) if item.aliases else ""
        extra = f" | 别名: {alias}" if alias else ""
        summary = f" — {item.summary}" if item.summary else ""
        lines.append(f"- `{item.doc_id}` {item.title}{extra}{summary}")
    return "\n".join(lines)


def parse_picked_ids(raw: str, allowed: Set[str]) -> List[str]:
    """从模型输出里取出合法 doc_id 列表。"""
    text = str(raw or "").strip()
    if not text:
        return []
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    picked: List[str] = []
    seen: Set[str] = set()
    for item in data:
        doc_id = str(item or "").strip()
        if doc_id in allowed and doc_id not in seen:
            picked.append(doc_id)
            seen.add(doc_id)
        if len(picked) >= _MAX_PICK:
            break
    return picked


def keyword_pick(question: str, docs: Sequence[ContextDoc], *, limit: int = _MAX_PICK) -> List[str]:
    """目录 JSON 失败时，用标题/别名与问题的字面重合挑文档。"""
    tokens = _tokens(question)
    if not tokens:
        return []
    ranked: List[tuple] = []
    for item in docs:
        hay = " ".join((item.doc_id, item.title, item.summary, *item.aliases)).lower()
        score = sum(1 for token in tokens if token in hay)
        if score:
            ranked.append((score, item.doc_id))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [doc_id for _score, doc_id in ranked[:limit]]


def should_ask_model_to_pick(optional_docs: Sequence[ContextDoc]) -> bool:
    """可选文档很少时整包附上，避免多一次模型调用。"""
    return len(optional_docs) >= _ATTACH_ALL_IF_FEWER_THAN


def render_knowledge(docs: Sequence[ContextDoc], *, budget: int = _MAX_CHARS) -> str:
    parts: List[str] = []
    used = 0
    limit = max(0, int(budget))
    for item in docs:
        block = f"# {item.title}\n\n{item.body}".strip()
        if not block:
            continue
        if used + len(block) > limit:
            remain = limit - used
            if remain > 200:
                parts.append(block[:remain] + "\n\n[文档已截断]")
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts).strip()


def compose_knowledge(
    global_docs: Sequence[ContextDoc],
    selected: Sequence[ContextDoc],
) -> str:
    """先放挑中的 wiki/know_how，再填 global，避免 global 把预算占满后丢掉正文。"""
    picked = render_knowledge(selected, budget=_PICKED_RESERVE)
    remain = max(_MAX_CHARS - len(picked), 2000)
    globe = render_knowledge(_global_attach_order(global_docs), budget=remain)
    return "\n\n".join(part for part in (picked, globe) if part)


def pick_optional_docs(
    question: str,
    optional: Sequence[ContextDoc],
    *,
    picked_ids: Optional[Sequence[str]] = None,
) -> List[ContextDoc]:
    """按模型选出的 id 取正文；没有合法 id 则退回关键词。"""
    if not optional:
        return []
    if len(optional) < _ATTACH_ALL_IF_FEWER_THAN:
        return list(optional)
    by_id: Dict[str, ContextDoc] = {item.doc_id: item for item in optional}
    allowed = set(by_id)
    ids = [doc_id for doc_id in (picked_ids or []) if doc_id in allowed][:_MAX_PICK]
    if not ids:
        ids = keyword_pick(question, optional)
    return [by_id[doc_id] for doc_id in ids if doc_id in by_id]


def _split_frontmatter(text: str) -> tuple:
    raw = str(text or "")
    if not raw.startswith("---"):
        return {}, raw
    rest = raw[3:].lstrip("\n")
    marker = re.search(r"\n---\s*\n", rest)
    if marker is None:
        return {}, raw
    meta_raw = rest[: marker.start()]
    body = rest[marker.end() :]
    try:
        meta = yaml.safe_load(meta_raw) or {}
    except yaml.YAMLError:
        return {}, raw
    if not isinstance(meta, Mapping):
        return {}, raw
    return dict(meta), body


def _heading_title(body: str) -> str:
    for line in str(body or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _string_tuple(value: object) -> tuple:
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        items = [str(item).strip() for item in value]
        return tuple(item for item in items if item)
    return ()


def _global_attach_order(docs: Sequence[ContextDoc]) -> List[ContextDoc]:
    def sort_key(item: ContextDoc) -> tuple:
        name = item.doc_id.rsplit("/", 1)[-1]
        if name == "system_role":
            return (0, 0, item.doc_id)
        return (1, len(item.body), item.doc_id)

    return sorted(docs, key=sort_key)


def _tokens(text: str) -> List[str]:
    lowered = str(text or "").lower()
    parts: List[str] = re.findall(r"[a-z0-9_]{2,}", lowered)
    seen = set(parts)
    for block in re.findall(r"[\u4e00-\u9fff]+", lowered):
        if len(block) < 2:
            continue
        candidates = [block]
        for size in (2, 3, 4):
            if len(block) >= size:
                candidates.extend(block[i : i + size] for i in range(len(block) - size + 1))
        for token in candidates:
            if token not in seen:
                seen.add(token)
                parts.append(token)
    return parts[:48]
