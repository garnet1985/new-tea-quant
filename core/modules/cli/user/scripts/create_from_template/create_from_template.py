"""从模板新建策略 / Tag（``cli.py -n`` / ``cli.py t -n``）。"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from core.infra.project_context import ProjectContext

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
_STRATEGY_TEMPLATE_REL = Path("_template") / "empty_strategy"
_TAG_TEMPLATE_REL = Path("_template") / "empty_scenario"


class CreateFromTemplate:
    """复制 userspace ``_template`` 并启用新建实体。"""

    class Error(ValueError):
        """从模板新建失败。"""

    @dataclass(frozen=True)
    class Result:
        kind: Literal["strategy", "tag"]
        key: str
        dest: Path

    @classmethod
    def create_strategy(cls, raw_path: str) -> CreateFromTemplate.Result:
        from core.modules.strategy import Strategy

        return cls._create(
            kind="strategy",
            raw_path=raw_path,
            root=ProjectContext.path.get_strategies_root(),
            template_rel=_STRATEGY_TEMPLATE_REL,
            path_validator=Strategy.is_valid_path,
        )

    @classmethod
    def create_tag(cls, raw_path: str) -> CreateFromTemplate.Result:
        from core.modules.tag import Tag

        return cls._create(
            kind="tag",
            raw_path=raw_path,
            root=ProjectContext.path.get_tags_root(),
            template_rel=_TAG_TEMPLATE_REL,
            path_validator=Tag.is_valid_path,
        )

    @classmethod
    def _create(
        cls,
        *,
        kind: Literal["strategy", "tag"],
        raw_path: str,
        root: Path,
        template_rel: Path,
        path_validator: Callable[[str], bool],
    ) -> CreateFromTemplate.Result:
        dest, key = cls._resolve_dest(
            root=root,
            raw_path=raw_path,
            path_validator=path_validator,
        )
        template = (root / template_rel).resolve()
        cls._copy_template(template=template, dest=dest)
        settings = dest / "settings.py"
        cls._enable_in_settings(settings)
        cls._inject_meta_key(settings, key)
        return cls.Result(kind=kind, key=key, dest=dest)

    @classmethod
    def _resolve_dest(
        cls,
        *,
        root: Path,
        raw_path: str,
        path_validator: Callable[[str], bool],
    ) -> tuple[Path, str]:
        text = str(raw_path or "").strip()
        if not text:
            raise cls.Error("目标路径不能为空")

        candidate = Path(text).expanduser()
        root_resolved = root.resolve()

        if candidate.is_absolute():
            dest = candidate.resolve()
            try:
                key = dest.relative_to(root_resolved).as_posix()
            except ValueError as exc:
                raise cls.Error(f"目标路径须在 {root_resolved} 下") from exc
        else:
            key = text.strip("/")
            dest = (root_resolved / key).resolve()

        if not key or key.startswith(".."):
            raise cls.Error("目标路径无效")

        if not path_validator(key):
            raise cls.Error(
                "路径须为 machine-readable：每段以字母开头，仅含字母、数字、下划线"
                f"（当前: {key!r}）"
            )

        return dest, key

    @classmethod
    def _copy_template(cls, *, template: Path, dest: Path) -> None:
        if not template.is_dir():
            raise cls.Error(f"模板目录不存在: {template}")
        if dest.exists():
            raise cls.Error(f"目标已存在: {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(template, dest, ignore=_IGNORE)

    @classmethod
    def _enable_in_settings(cls, settings_file: Path) -> None:
        if not settings_file.is_file():
            raise cls.Error(f"复制后缺少 settings.py: {settings_file}")
        text = settings_file.read_text(encoding="utf-8")
        new_text, count = re.subn(r'("is_enabled"\s*:\s*)False', r"\1True", text, count=1)
        if count != 1:
            raise cls.Error(f"无法在 {settings_file} 中将 is_enabled 设为 True")
        settings_file.write_text(new_text, encoding="utf-8")

    @classmethod
    def _inject_meta_key(cls, settings_file: Path, key: str) -> None:
        if not settings_file.is_file():
            raise cls.Error(f"缺少 settings.py: {settings_file}")
        text = settings_file.read_text(encoding="utf-8")
        if re.search(r'["\']key["\']\s*:', text):
            return

        escaped = str(key or "").strip().replace("\\", "\\\\").replace('"', '\\"')
        if not escaped:
            raise cls.Error("meta.key 不能为空")

        patterns = (
            (r'("meta"\s*:\s*\{)(\s*\n)', rf'\1\n        "key": "{escaped}",\2'),
            (r'("meta"\s*:\s*\{)(\s*\})', rf'\1\n        "key": "{escaped}",\n    \2'),
        )
        for pattern, repl in patterns:
            new_text, count = re.subn(pattern, repl, text, count=1)
            if count == 1:
                settings_file.write_text(new_text, encoding="utf-8")
                return
        raise cls.Error(f"无法在 {settings_file} 中注入 meta.key")
