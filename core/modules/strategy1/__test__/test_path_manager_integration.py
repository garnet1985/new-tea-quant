"""
PathManager Strategy API 集成测试
"""
import sys
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from core.infra.project_context import PathManager


class TestPathManagerStrategyAPI:
    """PathManager Strategy API 测试类"""
    
    def test_strategy_opportunity_enums_test_mode(self):
        """测试枚举器结果目录（test 模式）"""
        path = PathManager.strategy_opportunity_enums("test_strategy", use_sampling=True)
        
        assert "test_strategy" in str(path)
        assert "opportunity_enums" in str(path)
        assert path.name == "test"
    
    def test_strategy_opportunity_enums_output_mode(self):
        """测试枚举器结果目录（output 模式）"""
        path = PathManager.strategy_opportunity_enums("test_strategy", use_sampling=False)
        
        assert "test_strategy" in str(path)
        assert "opportunity_enums" in str(path)
        assert path.name == "output"
    
    def test_strategy_simulations_price_factor(self):
        """测试价格因子模拟器结果目录"""
        path = PathManager.strategy_simulations_price_factor("test_strategy")
        
        assert "test_strategy" in str(path)
        assert "simulations" in str(path)
        assert "price_factor" in str(path)
    
    def test_strategy_capital_allocation(self):
        """测试资金分配模拟器结果目录"""
        path = PathManager.strategy_capital_allocation("test_strategy")
        
        assert "test_strategy" in str(path)
        assert "capital_allocation" in str(path)
    
    def test_strategy_scan_cache(self):
        """测试扫描缓存目录"""
        path = PathManager.strategy_scan_cache("test_strategy")
        
        assert "test_strategy" in str(path)
        assert "scan_cache" in str(path)
    
    def test_strategy_scan_results(self):
        """测试扫描结果目录"""
        path = PathManager.strategy_scan_results("test_strategy")
        
        assert "test_strategy" in str(path)
        assert "results" in str(path)
        assert "scan" in str(path)
    
    def test_strategy_api_consistency(self):
        """测试 API 一致性（所有 API 都基于 strategy_results）"""
        strategy_name = "test_strategy"
        
        results_path = PathManager.strategy_results(strategy_name)
        enums_path = PathManager.strategy_opportunity_enums(strategy_name)
        price_factor_path = PathManager.strategy_simulations_price_factor(strategy_name)
        capital_path = PathManager.strategy_capital_allocation(strategy_name)
        scan_path = PathManager.strategy_scan_results(strategy_name)
        
        # 验证所有路径都基于 results_path
        assert enums_path.parent.parent == results_path
        assert price_factor_path.parent.parent == results_path
        assert capital_path.parent.parent == results_path
        assert scan_path.parent == results_path
