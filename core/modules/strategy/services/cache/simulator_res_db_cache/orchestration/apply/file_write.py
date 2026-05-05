"""与 ``core.ui.bff.shared.file_ops`` 同语义，避免经 ``ui.bff.shared`` 包导入触发 Flask 等依赖。"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def atomic_write_text(target_path: Path, content: str, encoding: str = "utf-8") -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding=encoding, dir=target_path.parent, delete=False) as tmp:
        tmp.write(content)
        temp_path = Path(tmp.name)
    os.replace(str(temp_path), str(target_path))


def backup_file(src_path: Path, backup_suffix: str = ".bak", encoding: str = "utf-8") -> Path:
    backup_path = src_path.with_suffix(src_path.suffix + backup_suffix)
    if src_path.exists():
        backup_path.write_text(src_path.read_text(encoding=encoding), encoding=encoding)
    return backup_path


__all__ = ["atomic_write_text", "backup_file"]
