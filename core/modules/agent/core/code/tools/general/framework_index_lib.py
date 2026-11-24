"""Parse / match NTQ framework_index (local markdown or remote JSON entries)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_WIKI_ROOT = Path(__file__).resolve().parents[3] / "content" / "ntq_wiki"
_LOCAL_INDEX = _WIKI_ROOT / "framework_index.md"

_FIELD_RE = re.compile(
    r"^-\s*(keywords|wiki|module|code|note)\s*:\s*(.*)\s*$",
    re.IGNORECASE,
)


def local_index_path() -> Path:
    return _LOCAL_INDEX


def parse_index_markdown(text: str) -> List[Dict[str, Any]]:
    """Parse ``framework_index.md`` ``##`` sections into entry dicts."""
    body = text
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4 :].lstrip("\n")

    entries: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for raw in body.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            if current and current.get("title"):
                entries.append(_finalize_entry(current))
            title = line[3:].strip()
            current = {
                "id": _slug(title),
                "title": title,
                "keywords": [],
                "wiki": "",
                "module": "",
                "code": [],
                "note": "",
            }
            continue
        if current is None:
            continue
        m = _FIELD_RE.match(line)
        if not m:
            continue
        key = m.group(1).lower()
        val = m.group(2).strip()
        if key == "keywords":
            current["keywords"] = _split_keywords(val)
        elif key == "code":
            current["code"] = [p.strip() for p in val.split(";") if p.strip()]
        elif key in ("wiki", "module", "note"):
            current[key] = val
    if current and current.get("title"):
        entries.append(_finalize_entry(current))
    return entries


def normalize_remote_entries(raw: Any) -> List[Dict[str, Any]]:
    """Normalize API ``entries`` list into the same shape as local parse."""
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        keywords = row.get("keywords")
        if isinstance(keywords, str):
            kw = _split_keywords(keywords)
        elif isinstance(keywords, list):
            kw = [str(k).strip() for k in keywords if str(k).strip()]
        else:
            kw = []
        code = row.get("code")
        if isinstance(code, str):
            codes = [p.strip() for p in code.replace("\n", ";").split(";") if p.strip()]
        elif isinstance(code, list):
            codes = [str(p).strip() for p in code if str(p).strip()]
        else:
            codes = []
        entry = {
            "id": str(row.get("id") or "").strip() or _slug(title),
            "title": title,
            "keywords": kw,
            "wiki": str(row.get("wiki") or "").strip(),
            "module": str(row.get("module") or "").strip(),
            "code": codes,
            "note": str(row.get("note") or "").strip(),
        }
        out.append(_finalize_entry(entry))
    return out


def load_local_entries() -> List[Dict[str, Any]]:
    path = local_index_path()
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parse_index_markdown(text)


def match_entries(
    query: str,
    entries: Sequence[Dict[str, Any]],
    *,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Score entries by keyword / title hits; return top matches."""
    q = (query or "").strip().lower()
    if not q or not entries:
        return []
    scored: List[tuple[int, Dict[str, Any]]] = []
    for entry in entries:
        score = _score(q, entry)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("title") or "")))
    return [dict(e) for _, e in scored[: max(1, min(20, int(limit or 5)))]]


def _score(query: str, entry: Dict[str, Any]) -> int:
    score = 0
    title = str(entry.get("title") or "").lower()
    if query in title:
        score += 8
    for kw in entry.get("keywords") or []:
        k = str(kw).lower()
        if not k:
            continue
        if k in query or query in k:
            score += 5
        elif len(k) >= 2 and k in title:
            score += 1
    wiki = str(entry.get("wiki") or "").lower()
    if query in wiki:
        score += 2
    note = str(entry.get("note") or "").lower()
    if query in note:
        score += 1
    return score


def _split_keywords(val: str) -> List[str]:
    parts = re.split(r"[,，、|/]+", val)
    return [p.strip() for p in parts if p.strip()]


def _slug(title: str) -> str:
    s = re.sub(r"\s+", "_", title.strip().lower())
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "", s, flags=re.UNICODE)
    return s[:64] or "entry"


def _finalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(entry.get("id") or _slug(str(entry.get("title") or "entry"))),
        "title": str(entry.get("title") or "").strip(),
        "keywords": list(entry.get("keywords") or []),
        "wiki": str(entry.get("wiki") or "").strip(),
        "module": str(entry.get("module") or "").strip(),
        "code": list(entry.get("code") or []),
        "note": str(entry.get("note") or "").strip(),
    }
