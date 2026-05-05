"""settings dict → 可写入 ``settings.py`` 的文本；备份与 ``core.ui.bff.shared.file_ops`` 对齐。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .file_write import backup_file


def _format_python_literal(value: Any, level: int = 0) -> str:
    indent_unit = "    "
    current_indent = indent_unit * level
    next_indent = indent_unit * (level + 1)

    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        items = list(value.items())
        for idx, (k, v) in enumerate(items):
            comma = "," if idx < len(items) - 1 else ""
            rendered = _format_python_literal(v, level + 1)
            if "\n" in rendered:
                lines.append(f"{next_indent}{repr(k)}: {rendered}{comma}")
            else:
                lines.append(f"{next_indent}{repr(k)}: {rendered}{comma}")
        lines.append(f"{current_indent}}}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"
        lines = ["["]
        for idx, item in enumerate(value):
            comma = "," if idx < len(value) - 1 else ""
            rendered = _format_python_literal(item, level + 1)
            if "\n" in rendered:
                lines.append(f"{next_indent}{rendered}{comma}")
            else:
                lines.append(f"{next_indent}{rendered}{comma}")
        lines.append(f"{current_indent}]")
        return "\n".join(lines)

    return repr(value)


def settings_dict_to_settings_py_source(
    settings_dict: Dict[str, Any],
    *,
    pretty: bool = True,
) -> str:
    """生成 ``settings = { ... }`` 形式模块正文（与 BFF 工作台写入语义对齐）。"""
    if pretty:
        formatted = _format_python_literal(settings_dict)
    else:
        formatted = repr(settings_dict)
    return (
        "# Written by simulator_res_db_cache.apply_cache.\n"
        "# Manual edits are allowed; subsequent saves may reformat.\n\n"
        f"settings = {formatted}\n"
    )


def backup_existing_settings_file(path: Path | str) -> None:
    """若文件已存在则写入 ``.py.bak`` 备份（与 ``backup_file`` 一致）。"""
    p = Path(path)
    if p.is_file():
        backup_file(p)


__all__ = ["backup_existing_settings_file", "settings_dict_to_settings_py_source"]
