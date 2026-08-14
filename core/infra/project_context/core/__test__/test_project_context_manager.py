"""ProjectContext 门面行为补充测试（详细断言；契约 smoke 见 __test__/test_api.py）。"""
import pytest
from pathlib import Path

from core.infra.project_context import ProjectContext


class TestProjectContextDetails:
    """ProjectContext 详细行为（非 test_api 契约 smoke）。"""

    def test_get_project_root_has_repo_marker(self):
        root = ProjectContext.path.get_project_root()
        assert (root / ".git").exists() or (root / "pyproject.toml").exists()

    def test_core_version_semver_when_present(self):
        version = ProjectContext.meta.core_version()
        if version is not None:
            assert len(version.split(".")) == 3

    def test_core_info_has_version_when_present(self):
        core_info = ProjectContext.meta.core_info()
        if core_info is not None:
            assert "version" in core_info

    def test_coerce_strategy_folder_relative(self):
        rel = "demo/example"
        folder = ProjectContext.path.coerce_strategy_folder(rel)
        assert folder == ProjectContext.path.get_strategies_root() / rel

    def test_coerce_strategy_folder_absolute(self, tmp_path: Path):
        abs_folder = tmp_path / "discovered" / "strategy"
        abs_folder.mkdir(parents=True)
        assert ProjectContext.path.coerce_strategy_folder(abs_folder) == abs_folder

    def test_get_backup_data_directory_under_backup(self):
        backup_data = ProjectContext.path.get_backup_data_directory()
        assert backup_data.parent == ProjectContext.path.get_backup_directory()
