"""按白名单加载 agent/context 下的短文（不做全库 RAG）。"""

from __future__ import annotations

from pathlib import Path
from typing import List

# guide/docs.py → roles → core → agent → context
_CONTEXT_ROOT = Path(__file__).resolve().parents[3] / "context"


def load_allowlisted_docs(allowlist_name: str, *, max_chars: int = 12000) -> str:
    """``allowlist_name`` 如 ``docs_arch.allowlist``。"""
    allow_path = Path(__file__).with_name(allowlist_name)
    if not allow_path.is_file():
        return ""
    chunks: List[str] = []
    total = 0
    root = _CONTEXT_ROOT.resolve()
    for raw in allow_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rel = line.lstrip("/")
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if body.startswith("---"):
            end = body.find("\n---", 3)
            if end != -1:
                body = body[end + 4 :].lstrip("\n")
        piece = f"### {rel}\n{body.strip()}\n"
        if total + len(piece) > max_chars:
            remain = max_chars - total
            if remain < 200:
                break
            piece = piece[:remain] + "\n…\n"
            chunks.append(piece)
            break
        chunks.append(piece)
        total += len(piece)
    return "\n".join(chunks).strip()
