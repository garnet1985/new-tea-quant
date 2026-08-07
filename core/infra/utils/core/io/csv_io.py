#!/usr/bin/env python3
"""CSV ↔ List[dict]（内部实现；公开入口 ``Utils.io``）。"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Sequence
import csv


class CsvIo:
    """List[dict] 与 CSV 互转。"""

    @staticmethod
    def _fieldnames(
        rows: List[Mapping[str, Any]],
        preferred_order: Optional[Sequence[str]] = None,
    ) -> List[str]:
        all_keys: set[str] = set()
        for row in rows:
            all_keys.update(row.keys())
        preferred = list(preferred_order or [])
        ordered = [k for k in preferred if k in all_keys]
        remaining = sorted(all_keys.difference(ordered))
        return ordered + remaining

    @staticmethod
    def write_dicts_to_csv(
        path: Path | str,
        rows: Iterable[Mapping[str, Any]],
        preferred_order: Optional[Sequence[str]] = None,
    ) -> None:
        """将字典行写入 CSV；列取并集，``preferred_order`` 优先。"""
        rows_list: List[Mapping[str, Any]] = list(rows)
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if not rows_list:
            path_obj.write_text("", encoding="utf-8")
            return

        fieldnames = CsvIo._fieldnames(rows_list, preferred_order)
        with path_obj.open("w", newline="", encoding="utf-8") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows_list:
                writer.writerow(row)

    @staticmethod
    def dicts_to_csv_bytes(
        rows: Iterable[Mapping[str, Any]],
        preferred_order: Optional[Sequence[str]] = None,
    ) -> bytes:
        """将字典行序列化为 CSV bytes。"""
        rows_list: List[Mapping[str, Any]] = list(rows)
        if not rows_list:
            return b""

        fieldnames = CsvIo._fieldnames(rows_list, preferred_order)
        sio = StringIO()
        writer = csv.DictWriter(sio, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_list:
            writer.writerow(row)
        return sio.getvalue().encode("utf-8")

    @staticmethod
    def csv_bytes_to_dicts(data: bytes) -> List[dict]:
        """CSV bytes → 字典列表。"""
        if not data:
            return []
        sio = StringIO(data.decode("utf-8"))
        return list(csv.DictReader(sio))

    @staticmethod
    def read_csv_to_dicts(path: Path | str) -> List[dict]:
        """从 CSV 文件读取字典列表；文件不存在返回 ``[]``。"""
        path_obj = Path(path)
        if not path_obj.exists():
            return []
        with path_obj.open("r", newline="", encoding="utf-8") as f_csv:
            return list(csv.DictReader(f_csv))


__all__ = ["CsvIo"]
