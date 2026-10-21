"""读写 userspace series_relation settings.py。"""

from __future__ import annotations

import pprint
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Mapping


def write_settings_py(path: Path, settings: Mapping[str, Any]) -> Path:
    """原子写入 ``settings = {...}``。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    literal = pprint.pformat(dict(settings or {}), width=88, sort_dicts=False)
    content = (
        "# Persisted by SeriesRelation (BFF / Facade).\n"
        "# Manual edits are allowed; next save may reformat this file.\n\n"
        f"settings = {literal}\n"
    )
    content = _maybe_black(content)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=target.parent, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)
    return target


def _maybe_black(content: str) -> str:
    try:
        import black
    except Exception:
        return content
    try:
        return black.format_str(
            content,
            mode=black.Mode(line_length=100, string_normalization=True),
        )
    except Exception:
        return content


__all__ = ["write_settings_py"]
