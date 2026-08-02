"""Utils 门面 — date / types / io / math。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Sequence

from core.infra.utils.date.date_utils import DateUtils
from core.infra.utils.type_utils import TypeUtils


class IoNamespace:
    """CSV / 归档 IO。"""

    @staticmethod
    def write_dicts_to_csv(
        path: Path | str,
        rows: Iterable[Mapping[str, Any]],
        preferred_order: Optional[Sequence[str]] = None,
    ) -> None:
        from core.infra.utils.io.csv_io import write_dicts_to_csv

        write_dicts_to_csv(path, rows, preferred_order=preferred_order)

    @staticmethod
    def read_csv_to_dicts(path: Path | str) -> List[dict]:
        from core.infra.utils.io.csv_io import read_csv_to_dicts

        return read_csv_to_dicts(path)

    @staticmethod
    def dicts_to_csv_bytes(
        rows: Iterable[Mapping[str, Any]],
        preferred_order: Optional[Sequence[str]] = None,
    ) -> bytes:
        from core.infra.utils.io.csv_io import dicts_to_csv_bytes

        return dicts_to_csv_bytes(rows, preferred_order=preferred_order)

    @staticmethod
    def csv_bytes_to_dicts(data: bytes) -> List[dict]:
        from core.infra.utils.io.csv_io import csv_bytes_to_dicts

        return csv_bytes_to_dicts(data)

    @staticmethod
    def write_archive(
        output_dir: str | Path,
        archive_name: str,
        files: Dict[str, bytes],
        *,
        format: Literal["tar.gz", "zip"] = "tar.gz",
    ) -> Path:
        from core.infra.utils.io.file_io import write_archive

        return write_archive(output_dir, archive_name, files, format=format)

    @staticmethod
    def read_archive_files(
        archive_path: str | Path,
        *,
        filter_ext: Optional[str] = None,
    ) -> Dict[str, bytes]:
        from core.infra.utils.io.file_io import read_archive_files

        return read_archive_files(archive_path, filter_ext=filter_ext)


class MathNamespace:
    """确定性随机等数值工具。"""

    @staticmethod
    def deterministic_unit_float(*key_parts: Any) -> float:
        from core.infra.utils.math.deterministic_random import deterministic_unit_float

        return deterministic_unit_float(*key_parts)


class Utils:
    """通用无业务工具门面（Facade）。"""

    date = DateUtils
    types = TypeUtils
    io = IoNamespace()
    math = MathNamespace()


__all__ = ["Utils"]
