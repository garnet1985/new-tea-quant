"""
ResultPathManager 单元测试
"""
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from core.modules.strategy.managers.result_path_manager import ResultPathManager


class TestResultPathManager:
    """ResultPathManager 测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.path_mgr = ResultPathManager(sim_version_dir=self.temp_dir)
    
    def teardown_method(self):
        """每个测试方法执行后的清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_ensure_root(self):
        """测试 ensure_root 方法"""
        root = self.path_mgr.ensure_root()
        
        assert root == self.temp_dir
        assert root.exists()
    
    def test_session_summary_path(self):
        """测试 session_summary_path"""
        path = self.path_mgr.session_summary_path()
        
        assert path.name == ResultPathManager.SESSION_SUMMARY_FILE
        assert path.parent == self.temp_dir
    
    def test_trades_path(self):
        """测试 trades_path"""
        path = self.path_mgr.trades_path()
        
        assert path.name == ResultPathManager.TRADES_FILE
        assert path.parent == self.temp_dir
    
    def test_equity_timeseries_path(self):
        """测试 equity_timeseries_path"""
        path = self.path_mgr.equity_timeseries_path()
        
        assert path.name == ResultPathManager.EQUITY_TIMESERIES_FILE
        assert path.parent == self.temp_dir
    
    def test_strategy_summary_path(self):
        """测试 strategy_summary_path"""
        path = self.path_mgr.strategy_summary_path()
        
        assert path.name == ResultPathManager.STRATEGY_SUMMARY_FILE
        assert path.parent == self.temp_dir
    
    def test_metadata_path(self):
        """测试 metadata_path"""
        path = self.path_mgr.metadata_path()
        
        assert path.name == ResultPathManager.METADATA_FILE
        assert path.parent == self.temp_dir
    
    def test_stock_json_path(self):
        """测试 stock_json_path"""
        stock_id = "000001.SZ"
        path = self.path_mgr.stock_json_path(stock_id)
        
        assert path.name == f"{stock_id}.json"
        assert path.parent == self.temp_dir
