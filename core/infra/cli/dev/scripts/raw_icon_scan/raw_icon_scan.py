#!/usr/bin/env python3
"""扫描运行时路径中的裸状态 emoji（应走 IconService / ``i()``）。

供 ``devcli.py pack`` / ``publish_prep`` 调用；也可独立运行::

    python -m core.infra.cli.dev.scripts.raw_icon_scan
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from core.infra.cmd_layout import i
from core.infra.cli.dev.services.paths import REPO_ROOT

# CLI / 日志常见状态图标（刻意白名单，避免误杀注释里的 ↔ 等符号）
_STATUS_EMOJIS: Tuple[str, ...] = (
    "✅",
    "❌",
    "⚠️",
    "⚠",
    "ℹ️",
    "ℹ",
    "🚀",
    "✨",
    "📦",
    "📁",
    "📂",
    "📄",
    "📝",
    "📋",
    "📌",
    "🔍",
    "🔎",
    "🎯",
    "💡",
    "🔥",
    "⭐",
    "⭐️",
    "🌟",
    "🎉",
    "📊",
    "📈",
    "📉",
    "🛠️",
    "🔧",
    "⚙️",
    "🏷️",
    "🗑️",
    "🗑",
    "▶️",
    "⏸",
    "⏸️",
    "⏭️",
    "🔄",
    "📅",
    "💰",
    "📤",
    "📥",
    "📎",
    "🔢",
    "💹",
    "🎮",
    "🔺",
    "🔻",
    "⏱️",
    "⏱",
    "⌛",
    "⏳",
    "📏",
    "👀",
    "💾",
    "🟢",
    "🔴",
    "🟠",
    "🟡",
    "🔵",
    "🟣",
    "⚪",
    "⚫",
    "🟤",
)

_EMOJI_RE = re.compile("|".join(re.escape(e) for e in sorted(_STATUS_EMOJIS, key=len, reverse=True)))

_SKIP_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        ".ntq",
        "node_modules",
        "build",
        "fed",
        "venv",
        ".venv",
        ".pytest_cache",
        "dist",
        "egg-info",
        "site-packages",
    }
)

# 图标定义与断言 emoji 字面量的测试：允许保留
_SKIP_PATH_SUBSTR = (
    "cmd_layout/icon/icon.py",
    "cmd_layout/icon/__test__/",
    "cmd_layout/__test__/",
    "cmd_layout/bar_chart/__test__/",
    "cli/dev/scripts/raw_icon_scan/",
)

_SCAN_ROOTS: Tuple[Path, ...] = (
    REPO_ROOT / "core",
    REPO_ROOT / "userspace",
)

_ROOT_PY_FILES: Tuple[Path, ...] = (
    REPO_ROOT / "install.py",
    REPO_ROOT / "launcher.py",
    REPO_ROOT / "cli.py",
    REPO_ROOT / "devcli.py",
)


@dataclass(frozen=True)
class RawIconHit:
    path: Path
    line: int
    snippet: str

    def format(self) -> str:
        return f"  {_rel_posix(self.path)}:{self.line}: {self.snippet}"


def _rel_posix(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _should_skip(path: Path) -> bool:
    rel = _rel_posix(path)
    return any(s in rel for s in _SKIP_PATH_SUBSTR)


def _iter_py_files(roots: Sequence[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            yield root
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            if _should_skip(path):
                continue
            yield path


def scan_raw_status_icons(
    *,
    roots: Sequence[Path] | None = None,
    root_files: Sequence[Path] | None = None,
) -> List[RawIconHit]:
    """返回裸状态 emoji 命中列表。"""
    hits: List[RawIconHit] = []
    files = list(_iter_py_files(roots or _SCAN_ROOTS))
    for path in root_files if root_files is not None else _ROOT_PY_FILES:
        if path.is_file() and not _should_skip(path):
            files.append(path)

    seen: set[Path] = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if not _EMOJI_RE.search(line):
                continue
            snippet = line.strip()
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            hits.append(RawIconHit(path=path, line=lineno, snippet=snippet))
    return hits


def run_raw_icon_scan(*, verbose: bool = True) -> int:
    """供 publish_prep 调用。0=通过，1=发现裸状态 emoji。"""
    hits = scan_raw_status_icons()
    if verbose:
        print(f"\n[检查] 裸状态 emoji（应使用 {i('success')} → i('…') / IconService）…", flush=True)
    if not hits:
        if verbose:
            print(
                f"  {i('success')} core/setup/userspace 与根入口无裸状态 emoji",
                flush=True,
            )
        return 0

    if verbose:
        print(
            f"  {i('error')} 发现 {len(hits)} 处裸状态 emoji；请改为 "
            f"`from core.infra.cmd_layout import i` + i('name')",
            flush=True,
        )
        for hit in hits[:80]:
            print(hit.format(), flush=True)
        if len(hits) > 80:
            print(f"  … 另有 {len(hits) - 80} 处未列出", flush=True)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="扫描裸状态 emoji（Windows 安全）")
    parser.add_argument("-q", "--quiet", action="store_true", help="仅返回退出码")
    args = parser.parse_args(list(argv) if argv is not None else None)
    return run_raw_icon_scan(verbose=not args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
