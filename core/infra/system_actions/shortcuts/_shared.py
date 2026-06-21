"""shortcuts 共用：路径校验、模板复制、settings 启用。"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Kind = Literal["strategy", "tag"]

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


class ScaffoldError(ValueError):
    """新建 userspace 实体失败。"""


@dataclass(frozen=True)
class ScaffoldResult:
    kind: Kind
    key: str
    dest: Path


def resolve_dest(*, root: Path, raw_path: str, path_validator) -> tuple[Path, str]:
    text = str(raw_path or "").strip()
    if not text:
        raise ScaffoldError("目标路径不能为空")

    candidate = Path(text).expanduser()
    root_resolved = root.resolve()

    if candidate.is_absolute():
        dest = candidate.resolve()
        try:
            key = dest.relative_to(root_resolved).as_posix()
        except ValueError as exc:
            raise ScaffoldError(f"目标路径须在 {root_resolved} 下") from exc
    else:
        key = text.strip("/")
        dest = (root_resolved / key).resolve()

    if not key or key.startswith(".."):
        raise ScaffoldError("目标路径无效")

    if not path_validator(key):
        raise ScaffoldError(
            "路径须为 machine-readable：每段以字母开头，仅含字母、数字、下划线"
            f"（当前: {key!r}）"
        )

    return dest, key


def copy_template(*, template: Path, dest: Path) -> None:
    if not template.is_dir():
        raise ScaffoldError(f"模板目录不存在: {template}")
    if dest.exists():
        raise ScaffoldError(f"目标已存在: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, dest, ignore=_IGNORE)


def enable_in_settings(settings_file: Path) -> None:
    if not settings_file.is_file():
        raise ScaffoldError(f"复制后缺少 settings.py: {settings_file}")
    text = settings_file.read_text(encoding="utf-8")
    new_text, count = re.subn(r'("is_enabled"\s*:\s*)False', r"\1True", text, count=1)
    if count != 1:
        raise ScaffoldError(f"无法在 {settings_file} 中将 is_enabled 设为 True")
    settings_file.write_text(new_text, encoding="utf-8")
