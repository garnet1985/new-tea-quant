"""
JobHelper 单元测试
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class TestJobHelper:
    """JobHelper 测试类"""
    
    def test_decide_worker_amount_100_or_less(self):
        """测试 decide_worker_amount（100个及以下）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper
        
        assert JobHelper.decide_worker_amount(50) == 1
        assert JobHelper.decide_worker_amount(100) == 1
    
    def test_decide_worker_amount_500_or_less(self):
        """测试 decide_worker_amount（500个及以下，100个以上）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper

        # 传入足够大的 max_workers，避免实现里 min(档位, os.cpu_count()) 在 CI 小核机器上压扁结果
        assert JobHelper.decide_worker_amount(101, max_workers=32) == 2
        assert JobHelper.decide_worker_amount(500, max_workers=32) == 2

    def test_decide_worker_amount_1000_or_less(self):
        """测试 decide_worker_amount（1000个及以下，500个以上）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper

        assert JobHelper.decide_worker_amount(501, max_workers=32) == 4
        assert JobHelper.decide_worker_amount(1000, max_workers=32) == 4

    def test_decide_worker_amount_2000_or_less(self):
        """测试 decide_worker_amount（2000个及以下，1000个以上）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper

        assert JobHelper.decide_worker_amount(1001, max_workers=32) == 8
        assert JobHelper.decide_worker_amount(2000, max_workers=32) == 8
    
    def test_decide_worker_amount_over_2000(self):
        """测试 decide_worker_amount（2000个以上）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper
        import os
        
        max_workers = os.cpu_count() or 10
        assert JobHelper.decide_worker_amount(2001) == max_workers
        assert JobHelper.decide_worker_amount(5000) == max_workers
    
    def test_decide_worker_amount_with_max_workers(self):
        """测试 decide_worker_amount（指定 max_workers）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper
        
        # 指定 max_workers 为 4
        assert JobHelper.decide_worker_amount(5000, max_workers=4) == 4
        # 即使 job 数量很多，也不会超过 max_workers
        assert JobHelper.decide_worker_amount(10000, max_workers=4) == 4
    
    def test_decide_worker_amount_with_auto(self):
        """测试 decide_worker_amount（max_workers="auto"）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper
        import os
        
        max_workers = os.cpu_count() or 10
        assert JobHelper.decide_worker_amount(5000, max_workers="auto") == max_workers
    
    def test_calculate_start_and_end_date_refresh_mode(self):
        """测试 calculate_start_and_end_date（REFRESH 模式）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper
        from core.modules.tag.core.enums import TagUpdateMode
        
        with patch('core.infra.project_context.ConfigManager.get_default_start_date') as mock_get_start, \
             patch('core.modules.data_manager.DataManager') as mock_data_mgr:
            
            mock_get_start.return_value = "20200101"
            
            mock_calendar = MagicMock()
            mock_calendar.get_latest_completed_trading_date.return_value = "20201231"
            mock_service = MagicMock()
            mock_service.calendar = mock_calendar
            mock_instance = MagicMock()
            mock_instance.service = mock_service
            mock_data_mgr.return_value = mock_instance
            
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.REFRESH,
                default_start_date="20200101",
                default_end_date="20201231"
            )
            
            assert start_date == "20200101"
            assert end_date == "20201231"
    
    def test_calculate_start_and_end_date_incremental_mode_with_last_date(self):
        """测试 calculate_start_and_end_date（INCREMENTAL 模式，有最后更新日期）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper
        from core.modules.tag.core.enums import TagUpdateMode
        
        with patch('core.modules.data_manager.DataManager') as mock_data_mgr:
            mock_tag_service = MagicMock()
            mock_tag_service.get_next_trading_date.return_value = "20200102"
            mock_calendar = MagicMock()
            mock_calendar.get_latest_completed_trading_date.return_value = "20201231"
            mock_service = MagicMock()
            mock_service.calendar = mock_calendar
            mock_stock = MagicMock()
            mock_stock.tags = mock_tag_service
            mock_instance = MagicMock()
            mock_instance.service = mock_service
            mock_instance.stock = mock_stock  # 添加 stock 属性
            mock_data_mgr.return_value = mock_instance
            
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.INCREMENTAL,
                entity_last_update_date="20200101",
                default_end_date="20201231"
            )
            
            assert start_date == "20200102"  # 下一个交易日
            assert end_date == "20201231"
    
    def test_calculate_start_and_end_date_incremental_mode_no_last_date(self):
        """测试 calculate_start_and_end_date（INCREMENTAL 模式，无最后更新日期）"""
        from core.modules.tag.core.components.helper.job_helper import JobHelper
        from core.modules.tag.core.enums import TagUpdateMode
        
        with patch('core.infra.project_context.ConfigManager.get_default_start_date') as mock_get_start, \
             patch('core.modules.data_manager.DataManager') as mock_data_mgr:
            
            mock_get_start.return_value = "20200101"
            
            mock_calendar = MagicMock()
            mock_calendar.get_latest_completed_trading_date.return_value = "20201231"
            mock_service = MagicMock()
            mock_service.calendar = mock_calendar
            mock_instance = MagicMock()
            mock_instance.service = mock_service
            mock_data_mgr.return_value = mock_instance
            
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.INCREMENTAL,
                entity_last_update_date=None,
                default_start_date="20200101",
                default_end_date="20201231"
            )
            
            assert start_date == "20200101"  # 使用默认开始日期
            assert end_date == "20201231"
