"""导入成功后清理临时演示包文件。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.setup.core.scripts.init_data.config import (
    GIT_DATA_META_NAME,
    GIT_DATA_ZIP_NAME,
)
from core.infra.setup.core.steps.import_data.installer import (
    EXTRACT_SUBDIR,
    SetupDataInstaller,
)

pytestmark = pytest.mark.force_run


def test_cleanup_temp_after_success_removes_package_and_extract(tmp_path: Path) -> None:
    data_dir = tmp_path / "install_demo"
    data_dir.mkdir()
    (data_dir / GIT_DATA_ZIP_NAME).write_bytes(b"PK\x03\x04x")
    (data_dir / GIT_DATA_META_NAME).write_text("{}", encoding="utf-8")
    extract = data_dir / EXTRACT_SUBDIR / "nested"
    extract.mkdir(parents=True)
    (extract / "a.csv").write_text("x", encoding="utf-8")
    progress = data_dir / ".import_progress.json"
    progress.write_text("{}", encoding="utf-8")

    inst = SetupDataInstaller(data_dir=data_dir, table_prefix="")
    inst._cleanup_temp_after_success(data_dir / EXTRACT_SUBDIR)

    assert not (data_dir / GIT_DATA_ZIP_NAME).exists()
    assert not (data_dir / GIT_DATA_META_NAME).exists()
    assert not (data_dir / EXTRACT_SUBDIR).exists()
    assert not progress.exists()
