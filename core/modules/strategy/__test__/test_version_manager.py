"""
VersionManager 单元测试
"""
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from core.modules.strategy.managers.version_manager import VersionManager
from core.infra.project_context import PathManager


class TestVersionManager:
    """VersionManager 测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        # 创建临时目录用于测试
        self.temp_dir = Path(tempfile.mkdtemp())
        self.strategy_name = "test_strategy"
        
        # Mock PathManager 返回临时目录
        self.path_manager_patcher = patch('core.modules.strategy.managers.version_manager.PathManager')
        self.mock_path_manager = self.path_manager_patcher.start()
        
        # 设置 strategy_results 返回临时目录
        self.results_dir = self.temp_dir / "results"
        self.mock_path_manager.strategy_results.return_value = self.results_dir
        
        # 设置 strategy_opportunity_enums 返回临时目录
        self.opportunity_enums_dir = self.results_dir / "opportunity_enums"
        self.mock_path_manager.strategy_opportunity_enums.return_value = self.opportunity_enums_dir / "test"
        
        # 设置其他路径
        self.mock_path_manager.strategy_simulations_price_factor.return_value = (
            self.results_dir / "simulations" / "price_factor"
        )
        self.mock_path_manager.strategy_capital_allocation.return_value = (
            self.results_dir / "capital_allocation"
        )
    
    def teardown_method(self):
        """每个测试方法执行后的清理"""
        self.path_manager_patcher.stop()
        # 清理临时目录
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_create_enumerator_version_first_time(self):
        """测试创建枚举器版本（首次创建）"""
        sub_dir = self.opportunity_enums_dir / "test"
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        version_dir, version_id = VersionManager.create_enumerator_version(
            strategy_name=self.strategy_name,
            use_sampling=True
        )
        
        assert version_id == 1
        assert version_dir.exists()
        assert version_dir.name == "1"
        assert (sub_dir / "meta.json").exists()
        
        # 验证 meta.json 内容
        with open(sub_dir / "meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["next_version_id"] == 2
        assert meta["strategy_name"] == self.strategy_name
        assert meta["mode"] == "test"
    
    def test_create_enumerator_version_incremental(self):
        """测试创建枚举器版本（递增版本号）"""
        sub_dir = self.opportunity_enums_dir / "test"
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建初始 meta.json
        meta_path = sub_dir / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"next_version_id": 5, "strategy_name": self.strategy_name}, f)
        
        version_dir, version_id = VersionManager.create_enumerator_version(
            strategy_name=self.strategy_name,
            use_sampling=True
        )
        
        assert version_id == 5
        assert version_dir.name == "5"
        
        # 验证 meta.json 已更新
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["next_version_id"] == 6
    
    def test_create_enumerator_version_output_mode(self):
        """测试创建枚举器版本（output 模式）"""
        output_dir = self.opportunity_enums_dir / "output"
        self.mock_path_manager.strategy_opportunity_enums.return_value = output_dir
        
        version_dir, version_id = VersionManager.create_enumerator_version(
            strategy_name=self.strategy_name,
            use_sampling=False
        )
        
        assert version_dir.exists()
        assert (output_dir / "meta.json").exists()
        
        with open(output_dir / "meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["mode"] == "output"
    
    def test_resolve_enumerator_version_latest(self):
        """测试解析枚举器版本（latest）"""
        sub_dir = self.opportunity_enums_dir / "test"
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建多个版本目录
        (sub_dir / "1").mkdir()
        (sub_dir / "2").mkdir()
        (sub_dir / "5").mkdir()
        
        version_dir, base_dir = VersionManager.resolve_enumerator_version(
            strategy_name=self.strategy_name,
            version_spec="test/latest"
        )
        
        assert version_dir.name == "5"  # 应该返回最新的版本
        assert base_dir == self.opportunity_enums_dir
    
    def test_resolve_enumerator_version_specific(self):
        """测试解析枚举器版本（指定版本号）"""
        sub_dir = self.opportunity_enums_dir / "test"
        sub_dir.mkdir(parents=True, exist_ok=True)
        (sub_dir / "3").mkdir()
        
        version_dir, base_dir = VersionManager.resolve_enumerator_version(
            strategy_name=self.strategy_name,
            version_spec="test/3"
        )
        
        assert version_dir.name == "3"
        assert base_dir == self.opportunity_enums_dir
    
    def test_resolve_enumerator_version_default_output(self):
        """测试解析枚举器版本（默认使用 output 目录）"""
        output_dir = self.opportunity_enums_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "2").mkdir()
        
        # 修改 mock 返回值
        self.mock_path_manager.strategy_opportunity_enums.return_value = output_dir
        
        version_dir, base_dir = VersionManager.resolve_enumerator_version(
            strategy_name=self.strategy_name,
            version_spec="2"
        )
        
        assert version_dir.name == "2"
    
    def test_resolve_enumerator_version_not_found(self):
        """测试解析枚举器版本（版本不存在）"""
        sub_dir = self.opportunity_enums_dir / "test"
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        with pytest.raises(FileNotFoundError):
            VersionManager.resolve_enumerator_version(
                strategy_name=self.strategy_name,
                version_spec="test/999"
            )
    
    def test_create_price_factor_version(self):
        """测试创建价格因子模拟器版本"""
        root_dir = self.results_dir / "simulations" / "price_factor"
        
        version_dir, version_id = VersionManager.create_price_factor_version(
            strategy_name=self.strategy_name
        )
        
        assert version_id == 1
        assert version_dir.exists()
        assert version_dir.name == "1"
        assert (root_dir / "meta.json").exists()
    
    def test_resolve_price_factor_version_latest(self):
        """测试解析价格因子模拟器版本（latest）"""
        root_dir = self.results_dir / "simulations" / "price_factor"
        root_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建多个版本目录
        (root_dir / "1").mkdir()
        (root_dir / "3").mkdir()
        (root_dir / "2").mkdir()
        
        version_dir, version_id = VersionManager.resolve_price_factor_version(
            strategy_name=self.strategy_name,
            version_spec="latest"
        )
        
        assert version_id == 3  # 应该返回最新的版本
        assert version_dir.name == "3"
    
    def test_create_capital_allocation_version(self):
        """测试创建资金分配模拟器版本"""
        base_dir = self.results_dir / "capital_allocation"
        
        version_dir, version_id = VersionManager.create_capital_allocation_version(
            strategy_name=self.strategy_name
        )
        
        assert version_id == 1
        assert version_dir.exists()
        assert version_dir.name == "1"
        assert (base_dir / "meta.json").exists()
    
    def test_resolve_capital_allocation_version_latest(self):
        """测试解析资金分配模拟器版本（latest）"""
        base_dir = self.results_dir / "capital_allocation"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建多个版本目录
        (base_dir / "1").mkdir()
        (base_dir / "5").mkdir()
        (base_dir / "2").mkdir()
        
        version_dir, version_id = VersionManager.resolve_capital_allocation_version(
            strategy_name=self.strategy_name,
            version_spec="latest"
        )
        
        assert version_id == 5  # 应该返回最新的版本
        assert version_dir.name == "5"
    
    def test_resolve_output_version(self):
        """测试解析输出版本（通用方法）"""
        sub_dir = self.opportunity_enums_dir / "test"
        sub_dir.mkdir(parents=True, exist_ok=True)
        (sub_dir / "4").mkdir()
        
        version_dir, sub_dir_path = VersionManager.resolve_output_version(
            strategy_name=self.strategy_name,
            output_version="test/4"
        )
        
        assert version_dir.name == "4"
        assert sub_dir_path == sub_dir
