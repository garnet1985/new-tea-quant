"""扫描产物句柄：``results/scan/{YYYYMMDD}/``（与仿真 version 并列，不复用）。

``ScanStore`` 只做路径 + json/csv 字节；Opportunity 编解码留在 scanner 引擎。
"""
from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.infra.utils import Utils
from core.modules.strategy.core.services.artifacts.consts import (
    SCAN_OPPORTUNITIES_FILE,
    SCAN_SUMMARY_FILE,
)
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

logger = logging.getLogger(__name__)

_SCAN_FILES = {
    "scan_summary": SCAN_SUMMARY_FILE,
    "opportunities": SCAN_OPPORTUNITIES_FILE,
}


def _encode_csv_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _decode_csv_cell(value: Any) -> Any:
    text = str(value) if value is not None else ""
    if text.startswith("{"):
        try:
            return json.loads(text)
        except Exception:
            return value
    return value


@dataclass
class ScanStore:
    """一次扫描日期目录的产物句柄。"""

    output_dir: Path
    scan_date: str
    strategy_folder: Path

    @classmethod
    def at(
        cls,
        strategy_folder: Union[str, Path],
        scan_date: str,
    ) -> "ScanStore":
        from core.modules.strategy.core.services.artifacts.store import ArtifactStore

        day = str(scan_date or "").strip()
        if not day:
            raise ValueError("scan date 不能为空")
        folder = Path(strategy_folder)
        return cls(
            output_dir=ArtifactStore.scan_root(folder) / day,
            scan_date=day,
            strategy_folder=folder,
        )

    def file(self, name: str) -> Path:
        filename = _SCAN_FILES.get(str(name or "").strip())
        if not filename:
            raise ValueError(f"unknown scan artifact file: {name!r}")
        return self.output_dir / filename

    def has_summary(self) -> bool:
        return self.file("scan_summary").is_file()

    def read_summary(self) -> Optional[Dict[str, Any]]:
        path = self.file("scan_summary")
        if not path.is_file():
            return None
        try:
            raw = ArtifactIO.read_json(path)
        except Exception as exc:
            logger.debug("读取 scan_summary 失败 date=%s: %s", self.scan_date, exc)
            return None
        return raw if isinstance(raw, dict) else None

    def write_summary(self, payload: Dict[str, Any]) -> Path:
        return ArtifactIO.write_json(self.file("scan_summary"), payload)

    def read_opportunity_rows(self) -> List[Dict[str, Any]]:
        path = self.file("opportunities")
        if not path.is_file():
            return []
        out: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    decoded = {
                        key: _decode_csv_cell(value) for key, value in row.items()
                    }
                    out.append(decoded)
        except Exception as exc:
            logger.warning("[ScanStore] load opportunities failed: %s", exc)
            return []
        return out

    def write_opportunity_rows(self, rows: List[Dict[str, Any]]) -> Optional[Path]:
        path = self.file("opportunities")
        if not rows:
            if path.is_file():
                try:
                    path.unlink()
                except OSError as exc:
                    logger.warning("删除空扫描 opportunities.csv 失败: %s", exc)
            return None
        encoded: List[Dict[str, Any]] = []
        for row in rows:
            encoded.append(
                {key: _encode_csv_cell(value) for key, value in dict(row or {}).items()}
            )
        all_keys = {k for row in encoded for k in row.keys()}
        Utils.io.write_dicts_to_csv(path, encoded, preferred_order=sorted(all_keys))
        return path

    @classmethod
    def prune(
        cls,
        strategy_folder: Union[str, Path],
        *,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        from core.modules.strategy.core.services.artifacts.store import ArtifactStore

        return ArtifactStore.prune_scan(strategy_folder, max_versions=max_versions)


__all__ = ["ScanStore"]
