from __future__ import annotations

import json
from pathlib import Path

from core.infra.setup.core.steps.import_data.align_data_window import align_data_json_to_pack_window
from core.infra.setup.core.steps.import_data.export.config import (
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
)


def test_creates_data_json_for_demo(tmp_path: Path) -> None:
    path = tmp_path / "system" / "config" / "data.json"
    out = align_data_json_to_pack_window(pack_kind="demo", userspace_data_json=path)
    assert out["changed"] is True
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["default_start_date"] == DEFAULT_START_DATE
    assert data["assumed_latest_completed_trading_date"] == DEFAULT_END_DATE


def test_overwrites_core_default_start_only(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text(
        json.dumps(
            {
                "default_start_date": "20080101",
                "assumed_latest_completed_trading_date": None,
                "keep_me": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = align_data_json_to_pack_window(pack_kind="member", userspace_data_json=path)
    assert out["changed"] is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["default_start_date"] == DEFAULT_START_DATE
    assert data["assumed_latest_completed_trading_date"] == DEFAULT_END_DATE
    assert data["keep_me"] is True


def test_preserves_user_custom_dates(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text(
        json.dumps(
            {
                "default_start_date": "20150101",
                "assumed_latest_completed_trading_date": "20201231",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = align_data_json_to_pack_window(pack_kind="demo", userspace_data_json=path)
    assert out["changed"] is False
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["default_start_date"] == "20150101"
    assert data["assumed_latest_completed_trading_date"] == "20201231"


def test_skips_full_pack(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    out = align_data_json_to_pack_window(pack_kind="full", userspace_data_json=path)
    assert out["skipped"] is True
    assert not path.exists()
