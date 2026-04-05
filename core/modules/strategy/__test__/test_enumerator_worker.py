"""
OpportunityEnumeratorWorker 单元测试
"""
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from core.modules.strategy.components.opportunity_enumerator.enumerator_worker import (
    OpportunityEnumeratorWorker
)


class TestOpportunityEnumeratorWorker:
    """OpportunityEnumeratorWorker 测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.strategy_name = "test_strategy"
        self.stock_id = "000001.SZ"
        
        # 基础 payload
        self.base_payload = {
            'stock_id': self.stock_id,
            'strategy_name': self.strategy_name,
            'settings': {
                'data': {
                    'base_price_source': 'stock_kline_daily',
                    'adjust_type': 'qfq',
                    'min_required_records': 200
                },
                'goal': {
                    'expiration': {'fixed_window_in_days': 30}
                }
            },
            'start_date': '20230101',
            'end_date': '20230110',
            'output_dir': str(self.temp_dir)
        }
    
    def teardown_method(self):
        """每个测试方法执行后的清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('core.modules.strategy.components.strategy_worker_data_manager.StrategyWorkerDataManager')
    @patch('importlib.import_module')
    @patch('core.modules.data_manager.DataManager')
    def test_init(self, mock_dm_class, mock_import_module, mock_strategy_worker_dm):
        """测试 Worker 初始化（Mock DataManager，避免 CI 无 PostgreSQL 时真实连库）"""
        mock_dm_class.return_value = MagicMock()

        mock_swdm_instance = MagicMock()
        mock_strategy_worker_dm.return_value = mock_swdm_instance

        # Mock 用户策略模块
        mock_strategy_module = MagicMock()
        mock_strategy_class = MagicMock()
        mock_strategy_module.StrategyWorker = mock_strategy_class
        mock_import_module.return_value = mock_strategy_module

        worker = OpportunityEnumeratorWorker(self.base_payload)

        assert worker.stock_id == self.stock_id
        assert worker.strategy_name == self.strategy_name
        assert worker.start_date == '20230101'
        assert worker.end_date == '20230110'
        mock_dm_class.assert_called_once_with(is_verbose=False)
        mock_strategy_worker_dm.assert_called_once()
    
    @patch('core.modules.strategy.components.strategy_worker_data_manager.StrategyWorkerDataManager')
    @patch('importlib.import_module')
    @patch('core.modules.data_manager.DataManager')
    def test_get_date_before(self, mock_dm_class, mock_import_module, mock_data_manager):
        """测试 _get_date_before 方法"""
        mock_dm_class.return_value = MagicMock()
        mock_data_manager.return_value = MagicMock()

        # Mock 用户策略模块
        mock_strategy_module = MagicMock()
        mock_strategy_class = MagicMock()
        mock_strategy_module.StrategyWorker = mock_strategy_class
        mock_import_module.return_value = mock_strategy_module

        worker = OpportunityEnumeratorWorker(self.base_payload)
        
        # 测试日期计算
        result = worker._get_date_before("20230110", 5)
        # 应该返回 5 个交易日前的日期
        assert result is not None
        assert len(result) == 8  # YYYYMMDD 格式
    
    @patch('core.modules.strategy.components.strategy_worker_data_manager.StrategyWorkerDataManager')
    @patch('importlib.import_module')
    @patch('core.modules.data_manager.DataManager')
    def test_run_no_klines(self, mock_dm_class, mock_import_module, mock_strategy_worker_dm):
        """测试 run 方法（无 K 线数据）"""
        mock_dm_class.return_value = MagicMock()
        mock_data_mgr_instance = MagicMock()
        mock_data_mgr_instance.get_klines.return_value = []
        mock_strategy_worker_dm.return_value = mock_data_mgr_instance

        mock_strategy_module = MagicMock()
        mock_strategy_module.StrategyWorker = MagicMock()
        mock_import_module.return_value = mock_strategy_module

        worker = OpportunityEnumeratorWorker(self.base_payload)
        result = worker.run()
        
        assert result['success'] is True
        assert result['opportunity_count'] == 0
        assert result['stock_id'] == self.stock_id
    
    @patch('core.modules.strategy.components.strategy_worker_data_manager.StrategyWorkerDataManager')
    @patch('importlib.import_module')
    @patch('core.modules.data_manager.DataManager')
    def test_run_with_klines_no_opportunities(self, mock_dm_class, mock_import_module, mock_strategy_worker_dm):
        """测试 run 方法（有 K 线但无机会）"""
        mock_dm_class.return_value = MagicMock()
        mock_data_mgr_instance = MagicMock()
        # Mock K 线数据
        mock_klines = [
            {'date': '20230101', 'close': 10.0},
            {'date': '20230102', 'close': 10.5},
        ]
        mock_data_mgr_instance.get_klines.return_value = mock_klines
        mock_data_mgr_instance.get_data_until.return_value = {'klines': mock_klines}
        mock_strategy_worker_dm.return_value = mock_data_mgr_instance

        # Mock strategy instance (不返回机会)
        mock_strategy = MagicMock()
        mock_strategy.scan_opportunity.return_value = None
        mock_data_mgr_instance.get_strategy_instance.return_value = mock_strategy

        mock_strategy_module = MagicMock()
        mock_strategy_module.StrategyWorker = MagicMock()
        mock_import_module.return_value = mock_strategy_module

        worker = OpportunityEnumeratorWorker(self.base_payload)
        result = worker.run()
        
        assert result['success'] is True
        assert result['opportunity_count'] == 0
    
    @patch('core.modules.strategy.components.strategy_worker_data_manager.StrategyWorkerDataManager')
    @patch('importlib.import_module')
    @patch('core.modules.data_manager.DataManager')
    def test_save_stock_results(self, mock_dm_class, mock_import_module, mock_strategy_worker_dm):
        """测试保存股票结果"""
        mock_dm_class.return_value = MagicMock()
        mock_strategy_worker_dm.return_value = MagicMock()

        mock_strategy_module = MagicMock()
        mock_strategy_module.StrategyWorker = MagicMock()
        mock_import_module.return_value = mock_strategy_module

        worker = OpportunityEnumeratorWorker(self.base_payload)
        
        # Mock opportunities
        opportunities = [
            {
                'opportunity_id': '1',
                'stock_id': self.stock_id,
                'trigger_date': '20230101',
                'status': 'active',
                'completed_targets': [
                    {'date': '20230105', 'type': 'take_profit', 'price': 11.0}
                ]
            }
        ]
        
        worker._save_stock_results(self.temp_dir, opportunities)
        
        # 验证文件已创建
        opp_file = self.temp_dir / f"{self.stock_id}_opportunities.csv"
        targets_file = self.temp_dir / f"{self.stock_id}_targets.csv"
        
        assert opp_file.exists()
        assert targets_file.exists()
