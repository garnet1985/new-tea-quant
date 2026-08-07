"""Utils 门面 — date / types / io / math / markdown。"""

from __future__ import annotations

from typing import Any

from core.infra.utils.core.date.date_utils import DateUtils
from core.infra.utils.core.io.csv_io import CsvIo
from core.infra.utils.core.io.file_io import FileIo
from core.infra.utils.core.markdown import MarkdownMgr
from core.infra.utils.core.math.deterministic_random import DeterministicRandom
from core.infra.utils.core.type_utils import TypeUtils


class Io:
    """CSV / 归档 IO（挂载 ``CsvIo`` / ``FileIo``）。"""

    write_dicts_to_csv = staticmethod(CsvIo.write_dicts_to_csv)
    read_csv_to_dicts = staticmethod(CsvIo.read_csv_to_dicts)
    dicts_to_csv_bytes = staticmethod(CsvIo.dicts_to_csv_bytes)
    csv_bytes_to_dicts = staticmethod(CsvIo.csv_bytes_to_dicts)
    write_archive = staticmethod(FileIo.write_archive)
    read_archive_files = staticmethod(FileIo.read_archive_files)


class Math:
    """确定性随机等数值工具。"""

    @staticmethod
    def deterministic_unit_float(*key_parts: Any) -> float:
        return DeterministicRandom.unit_float(*key_parts)


class Utils:
    """通用无业务工具门面（Facade）。"""

    date = DateUtils
    types = TypeUtils
    io = Io
    math = Math
    markdown = MarkdownMgr


__all__ = ["Utils"]
