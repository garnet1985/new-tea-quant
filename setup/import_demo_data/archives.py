"""
扫描解压目录中的单表归档（*.tar.gz / *.zip），按逻辑表名分组并排序 part。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ARCHIVE_NAME = re.compile(
    r"^(?P<base>.+?)(?:_part(?P<part>\d+))?\.(tar\.gz|zip)$",
    re.IGNORECASE,
)


def _should_skip_archive_path(path: Path) -> bool:
    """跳过 macOS 资源分叉、__MACOSX 等无效归档。"""
    if "__MACOSX" in path.parts:
        return True
    name = path.name
    if name.startswith("._"):
        return True
    if name.startswith(".") and name not in (".", ".."):
        # .DS_Store 等
        return True
    return False


def is_data_archive(path: Path) -> bool:
    n = path.name.lower()
    return n.endswith(".tar.gz") or n.endswith(".zip")


def parse_archive_table_and_part(name: str) -> Optional[Tuple[str, Optional[int]]]:
    """
    返回 (逻辑表名, None 表示单文件全量，或 part 序号)。

    支持: sys_x.tar.gz、sys_x_part1.tar.gz
    """
    m = _ARCHIVE_NAME.match(name)
    if not m:
        return None
    base = m.group("base")
    part = m.group("part")
    if base.startswith("._"):
        return None
    return base, int(part) if part is not None else None


def collect_table_archives(root: Path) -> Dict[str, List[Path]]:
    """
    扫描 root 下所有数据归档，按表名分组；同一表多个 part 按序号排序。
    """
    buckets: Dict[str, List[Tuple[int, Path]]] = {}
    if not root.exists():
        return {}

    for p in sorted(root.rglob("*")):
        if not p.is_file() or not is_data_archive(p) or _should_skip_archive_path(p):
            continue
        parsed = parse_archive_table_and_part(p.name)
        if not parsed:
            continue
        table, part = parsed
        sort_key = part if part is not None else 0
        buckets.setdefault(table, []).append((sort_key, p))

    result: Dict[str, List[Path]] = {}
    for table, items in buckets.items():
        items.sort(key=lambda x: (x[0], str(x[1])))
        result[table] = [p for _, p in items]
    return result
