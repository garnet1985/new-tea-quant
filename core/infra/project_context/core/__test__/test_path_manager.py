"""
PathManager 单元测试
"""
import pytest
from pathlib import Path

from core.infra.project_context import ProjectContext


def _fake_repo_with_userspace(tmp_path: Path, *, with_strategies: bool = True, with_config: bool = False) -> Path:
    """在临时目录构造最小「含 userspace」仓库树（CI 检出未必自带 userspace/）。"""
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    (fake_root / "README.md").touch()
    us = fake_root / "userspace"
    us.mkdir()
    if with_strategies:
        (us / "strategies").mkdir()
    if with_config:
        (us / "system" / "config").mkdir(parents=True)
    return fake_root


class TestPathManager:
    """PathManager 测试类"""
    
    def test_get_root(self):
        """测试获取项目根目录"""
        root = ProjectContext.path.get_project_root()
        
        # 验证返回的是 Path 对象
        assert isinstance(root, Path)
        
        # 验证根目录存在
        assert root.exists()
        assert root.is_dir()
        
        # 验证根目录包含项目标记文件
        assert (root / "README.md").exists() or (root / ".git").exists()

    def test_get_python_resolvers(self):
        import os

        venv_py = ProjectContext.path.get_venv_python()
        sys_py = ProjectContext.path.get_sys_python()
        root = ProjectContext.path.get_project_root()
        expected_venv = root / "venv" / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        assert venv_py == expected_venv
        assert isinstance(sys_py, Path)
        assert sys_py.is_file()
        if venv_py.is_file():
            assert ProjectContext.path.get_python() == venv_py
            assert ProjectContext.path.get_python(allow_sys_fallback=False) == venv_py
        else:
            assert ProjectContext.path.get_python() == sys_py
            with pytest.raises(FileNotFoundError):
                ProjectContext.path.get_python(allow_sys_fallback=False)
    
    def test_core(self):
        """测试获取 core 目录"""
        core_dir = ProjectContext.path.get_core_root()
        
        assert isinstance(core_dir, Path)
        assert core_dir.exists()
        assert (core_dir / "infra").exists()
    
    def test_userspace(self, tmp_path, monkeypatch):
        """测试获取 userspace 目录（默认 <root>/userspace；仓库可不自带，由安装创建）"""
        from core.infra.project_context.core.path_manager import PathManager
        fake_root = _fake_repo_with_userspace(tmp_path, with_strategies=True)
        monkeypatch.delenv("NEW_TEA_QUANT_USERSPACE_ROOT", raising=False)
        monkeypatch.delenv("NTQ_USERSPACE_ROOT", raising=False)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        ProjectContext.cache.clear_userspace_cache()
        try:
            userspace_dir = ProjectContext.path.get_userspace_root()

            assert isinstance(userspace_dir, Path)
            assert userspace_dir == (fake_root / "userspace").resolve()
            assert userspace_dir.exists()
            assert (userspace_dir / "strategies").exists()
        finally:
            ProjectContext.cache.clear_userspace_cache()

    def test_config(self, tmp_path, monkeypatch):
        """测试获取 config 目录（userspace/system/config）"""
        from core.infra.project_context.core.path_manager import PathManager
        fake_root = _fake_repo_with_userspace(tmp_path, with_strategies=False, with_config=True)
        monkeypatch.delenv("NEW_TEA_QUANT_USERSPACE_ROOT", raising=False)
        monkeypatch.delenv("NTQ_USERSPACE_ROOT", raising=False)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        ProjectContext.cache.clear_userspace_cache()
        try:
            config_dir = ProjectContext.path.get_user_config_root()

            assert isinstance(config_dir, Path)
            assert config_dir == (
                fake_root / "userspace" / "system" / "config"
            ).resolve()
            assert config_dir.exists()
        finally:
            ProjectContext.cache.clear_userspace_cache()
    
    def test_strategy(self):
        """测试获取策略目录"""
        strategy_dir = ProjectContext.path.get_strategy_directory("example")
        
        assert isinstance(strategy_dir, Path)
        # 策略目录路径应该正确
        assert "example" in str(strategy_dir)

    def test_backup_paths(self):
        """备份目录落在 userspace/backup 约定下"""
        root = ProjectContext.path.get_project_root()
        backup_dir = ProjectContext.path.get_backup_directory()
        backup_data_dir = backup_dir / "data"

        assert isinstance(backup_dir, Path)
        assert isinstance(backup_data_dir, Path)
        assert backup_data_dir == backup_dir / "data"
        assert backup_dir.is_relative_to(root)
        assert "userspace" in backup_dir.parts and "system" in backup_dir.parts and "backup" in backup_dir.parts
    
    def test_root_caching(self):
        """测试根目录缓存"""
        root1 = ProjectContext.path.get_project_root()
        root2 = ProjectContext.path.get_project_root()
        
        # 应该返回同一个对象（缓存）
        assert root1 is root2

    def test_userspace_ntq_at_userspace_root(self, tmp_path, monkeypatch):
        from core.infra.project_context.core.path_manager import PathManager

        fake_root = _fake_repo_with_userspace(tmp_path, with_strategies=True)
        us = fake_root / "userspace"
        ntq_tmp = us / ".ntq" / "tmp"
        ntq_tmp.mkdir(parents=True)

        monkeypatch.delenv("NEW_TEA_QUANT_USERSPACE_ROOT", raising=False)
        monkeypatch.delenv("NTQ_USERSPACE_ROOT", raising=False)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        ProjectContext.cache.clear_userspace_cache()
        try:
            ntq = ProjectContext.path.get_userspace_ntq_directory()
            assert ntq == (us / ".ntq").resolve()
            assert ntq.is_dir()
            assert ProjectContext.path.get_userspace_tmp_directory() == ntq / "tmp"
        finally:
            ProjectContext.cache.clear_userspace_cache()

    def test_userspace_missing_configured_path_no_fallback(self, tmp_path, monkeypatch):
        """已配置但目录不存在时不静默回落。"""
        import json

        from core.infra.project_context.core.path_manager import PathManager

        fake_root = tmp_path / "repo"
        fake_root.mkdir()
        (fake_root / "README.md").touch()
        external = tmp_path / "外部 目录" / "my us"
        state = fake_root / ".ntq"
        state.mkdir()
        (state / "userspace-path.json").write_text(
            json.dumps({"userspacePath": str(external)}, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.delenv("NEW_TEA_QUANT_USERSPACE_ROOT", raising=False)
        monkeypatch.delenv("NTQ_USERSPACE_ROOT", raising=False)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        ProjectContext.cache.clear_userspace_cache()
        try:
            got = ProjectContext.path.get_userspace_root()
            assert got == external.resolve()
            assert not got.exists()
            assert got != (fake_root / "userspace").resolve()
        finally:
            ProjectContext.cache.clear_userspace_cache()

    def test_userspace_env_and_chinese_space(self, tmp_path, monkeypatch):
        from core.infra.project_context.core.path_manager import PathManager

        fake_root = tmp_path / "repo"
        fake_root.mkdir()
        (fake_root / "README.md").touch()
        external = tmp_path / "数据空间" / "my userspace"
        external.mkdir(parents=True)
        monkeypatch.setenv("NTQ_USERSPACE_ROOT", str(external))
        monkeypatch.delenv("NEW_TEA_QUANT_USERSPACE_ROOT", raising=False)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        ProjectContext.cache.clear_userspace_cache()
        try:
            assert ProjectContext.path.get_userspace_root() == external.resolve()
        finally:
            ProjectContext.cache.clear_userspace_cache()

    def test_resolve_userspace_target_empty_uses_state(self, tmp_path, monkeypatch):
        import json

        from core.infra.project_context.core.path_manager import PathManager

        fake_root = tmp_path / "repo"
        fake_root.mkdir()
        (fake_root / "README.md").touch()
        external = tmp_path / "kept us"
        external.mkdir()
        state = fake_root / ".ntq"
        state.mkdir()
        (state / "userspace-path.json").write_text(
            json.dumps({"userspacePath": str(external)}, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.delenv("NEW_TEA_QUANT_USERSPACE_ROOT", raising=False)
        monkeypatch.delenv("NTQ_USERSPACE_ROOT", raising=False)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        ProjectContext.cache.clear_userspace_cache()
        try:
            got = ProjectContext.path.resolve_userspace_target(None)
            assert got == external.resolve()
        finally:
            ProjectContext.cache.clear_userspace_cache()

    def test_resolve_userspace_target_rejects_file(self, tmp_path, monkeypatch):
        from core.infra.project_context.core.path_manager import PathManager

        fake_root = tmp_path / "repo"
        fake_root.mkdir()
        (fake_root / "README.md").touch()
        not_dir = tmp_path / "not_a_dir.txt"
        not_dir.write_text("x", encoding="utf-8")
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        with pytest.raises(ValueError, match="不是目录"):
            ProjectContext.path.resolve_userspace_target(not_dir)

    def test_userspace_bad_json_falls_back_default(self, tmp_path, monkeypatch):
        from core.infra.project_context.core.path_manager import PathManager

        fake_root = tmp_path / "repo"
        fake_root.mkdir()
        (fake_root / "README.md").touch()
        (fake_root / "userspace").mkdir()
        state = fake_root / ".ntq"
        state.mkdir()
        (state / "userspace-path.json").write_text("{not json", encoding="utf-8")
        monkeypatch.delenv("NEW_TEA_QUANT_USERSPACE_ROOT", raising=False)
        monkeypatch.delenv("NTQ_USERSPACE_ROOT", raising=False)
        monkeypatch.setattr(PathManager, "_root_cache", fake_root)
        ProjectContext.cache.clear_userspace_cache()
        try:
            assert ProjectContext.path.get_userspace_root() == (
                fake_root / "userspace"
            ).resolve()
        finally:
            ProjectContext.cache.clear_userspace_cache()
