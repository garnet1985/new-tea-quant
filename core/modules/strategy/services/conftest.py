"""Strategy services 层共享 pytest fixtures（不依赖仓库 userspace/）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Tuple

import pytest

from core.infra.project_context.path_manager import PathManager

_ENUM_REPORT_FILE = "0_report_enum.json"


def _write_enum_report(enum_root: Path, version_dir: str, *, opportunities: int) -> None:
    out_dir = enum_root / version_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "strategy_name": "unit_test",
        "enumMetrics": {"totalOpportunities": opportunities},
    }
    (out_dir / _ENUM_REPORT_FILE).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


@pytest.fixture
def enum_simulation_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    临时 ``.../simulations/enum`` 目录树，供 PathManager.get_strategy_directory_simulation_enum 使用。

    默认写入版本 ``9``（140 条机会）与 ``20``（23206 条，供 latest 解析测试）。
    """
    enum_root = tmp_path / "simulations" / "enum"
    for version_dir, count in (("9", 140), ("20", 23206)):
        _write_enum_report(enum_root, version_dir, opportunities=count)

    monkeypatch.setattr(
        PathManager,
        "strategy_simulation_enum",
        staticmethod(lambda _strategy_name: enum_root),
    )
    return enum_root


def write_enum_versions(
    enum_root: Path,
    versions: Iterable[Tuple[str, int]],
) -> None:
    """测试内按需追加 enum 版本目录。"""
    for version_dir, opportunities in versions:
        _write_enum_report(enum_root, version_dir, opportunities=opportunities)
