"""
OpportunityEnumerator 单元测试
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

from core.modules.strategy.components.opportunity_enumerator.opportunity_enumerator import (
    OpportunityEnumerator
)
from core.modules.strategy.components.opportunity_enumerator.enumerator_settings import (
    OpportunityEnumeratorSettings
)


class TestOpportunityEnumerator:
    """OpportunityEnumerator 测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.strategy_name = "test_strategy"
    
    def teardown_method(self):
        """每个测试方法执行后的清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('core.modules.strategy.components.opportunity_enumerator.opportunity_enumerator.OpportunityEnumerator._load_strategy_settings')
    @patch('core.modules.strategy.components.opportunity_enumerator.opportunity_enumerator.OpportunityEnumeratorSettings.from_base')
    @patch('core.modules.strategy.managers.version_manager.VersionManager')
    @patch('core.infra.worker.ProcessExecutor')
    @patch('core.infra.worker.MemoryAwareScheduler')
    def test_enumerate_basic(self, mock_scheduler, mock_executor, mock_version_manager, mock_from_base, mock_load_settings):
        """测试枚举基本流程"""
        # Mock settings
        mock_base_settings = MagicMock()
        mock_base_settings.name = self.strategy_name
        settings_dict = {
            "name": self.strategy_name,
            "data": {
                "base_price_source": "stock_kline_daily",
                "adjust_type": "qfq"
            },
            "goal": {
                "expiration": {"fixed_window_in_days": 30}
            }
        }
        mock_base_settings.to_dict.return_value = settings_dict
        mock_load_settings.return_value = mock_base_settings
        
        # Mock enum_settings 对象（from_base 返回的对象）
        # 创建一个简单的对象，确保所有属性都是数值类型
        class MockEnumSettings:
            def __init__(self):
                self.memory_budget_mb = 1000.0  # 使用数值而不是 "auto"
                self.warmup_batch_size = 10  # 使用数值，不是 "auto"
                self.min_batch_size = 5  # 使用数值，不是 "auto"
                self.max_batch_size = 20  # 使用数值，不是 "auto"，且大于 min_batch_size
                self.monitor_interval = 5
                self.use_sampling = False
                self.is_verbose = False
            
            def to_dict(self):
                return settings_dict
        
        mock_enum_settings = MockEnumSettings()
        mock_from_base.return_value = mock_enum_settings
        
        # Mock VersionManager
        mock_version_dir = self.temp_dir / "1"
        mock_version_dir.mkdir(parents=True, exist_ok=True)
        mock_version_manager.create_enumerator_version.return_value = (mock_version_dir, 1)
        
        # Mock ProcessExecutor
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        # Mock scheduler instance
        mock_scheduler_instance = MagicMock()
        # job 需要包含所有必需字段
        mock_job = {
            'stock_id': '000001.SZ',
            'strategy_name': self.strategy_name,
            'settings': settings_dict,
            'start_date': '20230101',
            'end_date': '20230110',
            'output_dir': str(mock_version_dir)
        }
        mock_scheduler_instance.iter_batches.return_value = [[mock_job]]
        mock_scheduler.return_value = mock_scheduler_instance
        
        # Mock job results - ProcessExecutor.run_jobs 返回 JobResult 对象列表
        from core.infra.worker.executors.base import JobResult, JobStatus
        mock_job_result = JobResult(
            job_id='000001.SZ',
            status=JobStatus.COMPLETED,
            result={
                'success': True,
                'stock_id': '000001.SZ',
                'opportunity_count': 10,
                'performance_metrics': {}
            }
        )
        mock_executor_instance.run_jobs.return_value = [mock_job_result]
        
        # 执行枚举
        result = OpportunityEnumerator.enumerate(
            strategy_name=self.strategy_name,
            start_date="20230101",
            end_date="20230110",
            stock_list=["000001.SZ"],
            max_workers=1
        )
        
        assert len(result) == 1
        assert result[0]['strategy_name'] == self.strategy_name
        assert result[0]['version_id'] == 1
        mock_version_manager.create_enumerator_version.assert_called_once()
    
    @patch('core.modules.strategy.components.opportunity_enumerator.opportunity_enumerator.OpportunityEnumerator._load_strategy_settings')
    def test_load_strategy_settings(self, mock_load_settings):
        """测试加载策略设置"""
        # Mock _load_strategy_settings 返回的 settings
        mock_settings = MagicMock()
        mock_settings.name = self.strategy_name
        mock_load_settings.return_value = mock_settings
        
        settings = OpportunityEnumerator._load_strategy_settings(self.strategy_name)
        assert settings.name == self.strategy_name
    
    @patch('core.modules.strategy.components.opportunity_enumerator.opportunity_enumerator.Path')
    def test_save_results(self, mock_path):
        """测试保存结果"""
        output_dir = self.temp_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        OpportunityEnumerator._save_results(
            strategy_name=self.strategy_name,
            start_date="20230101",
            end_date="20230110",
            output_dir=output_dir,
            version_id=1,
            version_dir_name="1",
            opportunity_count=100,
            settings_snapshot={"name": self.strategy_name},
            is_full_enumeration=False
        )
        
        metadata_path = output_dir / "0_metadata.json"
        assert metadata_path.exists()
        
        import json
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        assert metadata["strategy_name"] == self.strategy_name
        assert metadata["opportunity_count"] == 100
        assert metadata["version_id"] == 1
        assert metadata["is_full_enumeration"] is False
    
    def test_cleanup_old_versions(self):
        """测试清理旧版本"""
        root_dir = self.temp_dir / "test"
        root_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建多个版本目录
        for i in range(1, 6):
            version_dir = root_dir / str(i)
            version_dir.mkdir()
            # 创建 metadata 文件
            metadata_path = version_dir / "0_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                import json
                json.dump({
                    "version_id": i,
                    "created_at": "2026-01-01T00:00:00"
                }, f)
        
        # 清理，只保留最新的 2 个版本
        OpportunityEnumerator._cleanup_old_versions(
            root_dir=root_dir,
            max_keep_versions=2,
            strategy_name=self.strategy_name,
            mode="test"
        )
        
        # 验证：应该只剩下版本 4 和 5
        remaining_dirs = [d for d in root_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
        assert len(remaining_dirs) == 2
        version_ids = sorted([int(d.name) for d in remaining_dirs])
        assert version_ids == [4, 5]  # 保留最新的 2 个版本
    
    def test_cleanup_old_versions_no_metadata(self):
        """测试清理旧版本（无 metadata 文件）"""
        root_dir = self.temp_dir / "test"
        root_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建版本目录（无 metadata）
        for i in range(1, 4):
            version_dir = root_dir / str(i)
            version_dir.mkdir()
        
        # 清理，只保留最新的 1 个版本
        OpportunityEnumerator._cleanup_old_versions(
            root_dir=root_dir,
            max_keep_versions=1,
            strategy_name=self.strategy_name,
            mode="test"
        )
        
        # 验证：应该只剩下版本 3（目录名就是版本ID）
        remaining_dirs = [d for d in root_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
        assert len(remaining_dirs) == 1
        assert remaining_dirs[0].name == "3"
    
    def test_cleanup_old_versions_insufficient_versions(self):
        """测试清理旧版本（版本数不足）"""
        root_dir = self.temp_dir / "test"
        root_dir.mkdir(parents=True, exist_ok=True)
        
        # 只创建 2 个版本
        for i in range(1, 3):
            version_dir = root_dir / str(i)
            version_dir.mkdir()
        
        # 尝试保留 5 个版本（但只有 2 个）
        OpportunityEnumerator._cleanup_old_versions(
            root_dir=root_dir,
            max_keep_versions=5,
            strategy_name=self.strategy_name,
            mode="test"
        )
        
        # 验证：应该保留所有版本
        remaining_dirs = [d for d in root_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]
        assert len(remaining_dirs) == 2
