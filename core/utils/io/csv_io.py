#!/usr/bin/env python3
"""
通用 CSV 写入工具。

目标：
- 为「List[Dict] → CSV」提供统一的、健壮的实现
- 自动合并所有行的字段，避免 DictWriter 因额外字段报错
- 支持优先字段顺序，其他字段按名称排序附在后面
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, Optional, List
import csv
from io import StringIO


def write_dicts_to_csv(
    path: Path | str,
    rows: Iterable[Mapping[str, Any]],
    preferred_order: Optional[Sequence[str]] = None,
) -> None:
    """
    将一组字典写入 CSV 文件。

    行中可能存在字段不完全一致的情况，本函数会：
    - 先对所有行的 key 做并集，作为完整的列集合
    - preferred_order 中出现的列保持指定顺序，其余按字母序追加在后
    """
    rows_list: List[Mapping[str, Any]] = list(rows)
    if not rows_list:
        # 没有数据时，创建空文件即可（不写 header）
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text("", encoding="utf-8")
        return

    # 收集所有字段名
    all_keys = set()
    for r in rows_list:
        all_keys.update(r.keys())

    # 按 preferred_order + 其余字段排序
    preferred_order = list(preferred_order or [])
    ordered = [k for k in preferred_order if k in all_keys]
    remaining = sorted(all_keys.difference(ordered))
    fieldnames = ordered + remaining

    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with path_obj.open("w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows_list:
            writer.writerow(r)


def dicts_to_csv_bytes(
    rows: Iterable[Mapping[str, Any]],
    preferred_order: Optional[Sequence[str]] = None,
) -> bytes:
    """
    将一组字典序列化为 CSV bytes。

    - 会自动合并所有行的字段，保证列集合完整
    - preferred_order 指定的字段会优先排在前面
    """
    rows_list: List[Mapping[str, Any]] = list(rows)
    if not rows_list:
        return b""

    # 收集所有字段名
    all_keys = set()
    for r in rows_list:
        all_keys.update(r.keys())

    preferred_order = list(preferred_order or [])
    ordered = [k for k in preferred_order if k in all_keys]
    remaining = sorted(all_keys.difference(ordered))
    fieldnames = ordered + remaining

    sio = StringIO()
    writer = csv.DictWriter(sio, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows_list:
        writer.writerow(r)
    return sio.getvalue().encode("utf-8")


def csv_bytes_to_dicts(data: bytes) -> List[dict]:
    """
    将 CSV bytes 解析为字典列表。
    """
    if not data:
        return []
    text = data.decode("utf-8")
    sio = StringIO(text)
    reader = csv.DictReader(sio)
    return list(reader)


def read_csv_to_dicts(path: Path | str) -> List[dict]:
    """
    从 CSV 文件读取字典列表。
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return []
    with path_obj.open("r", newline="", encoding="utf-8") as f_csv:
        reader = csv.DictReader(f_csv)
        return list(reader)

