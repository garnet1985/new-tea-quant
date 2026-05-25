"""
JobHelper 单元测试
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


class TestJobHelper:
    """JobHelper 测试类"""

    def test_calculate_start_and_end_date_caps_user_end_to_latest(self):
        """场景 end_date 晚于 latest completed 时应截断。"""
        from core.modules.tag.components.helper.job_helper import JobHelper
        from core.modules.tag.enums import TagUpdateMode

        with patch.object(
            JobHelper,
            "_resolve_latest_completed_trading_date",
            return_value="20250601",
        ):
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.REFRESH,
                default_start_date="20200101",
                default_end_date="20251231",
            )

        assert start_date == "20200101"
        assert end_date == "20250601"

    def test_calculate_start_and_end_date_uses_latest_when_no_user_end(self):
        from core.modules.tag.components.helper.job_helper import JobHelper
        from core.modules.tag.enums import TagUpdateMode

        with patch.object(
            JobHelper,
            "_resolve_latest_completed_trading_date",
            return_value="20250601",
        ):
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.REFRESH,
                default_start_date="20200101",
            )

        assert end_date == "20250601"

    def test_calculate_start_and_end_date_incremental_mode_with_last_date(self):
        """测试 calculate_start_and_end_date（INCREMENTAL 模式，有最后更新日期）"""
        from core.modules.tag.components.helper.job_helper import JobHelper
        from core.modules.tag.enums import TagUpdateMode
        
        with patch('core.modules.tag.components.helper.job_helper.DateUtils.add_days') as mock_add_days, \
             patch.object(JobHelper, '_resolve_latest_completed_trading_date', return_value='20251231'):
            mock_add_days.return_value = "20200102"
            
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.INCREMENTAL,
                entity_last_update_date="20200101",
                default_end_date="20201231"
            )
            
            assert start_date == "20200102"  # 下一个交易日
            assert end_date == "20201231"
    
    def test_calculate_start_and_end_date_incremental_mode_no_last_date(self):
        """测试 calculate_start_and_end_date（INCREMENTAL 模式，无最后更新日期）"""
        from core.modules.tag.components.helper.job_helper import JobHelper
        from core.modules.tag.enums import TagUpdateMode
        
        with patch('core.infra.project_context.ConfigManager.get_default_start_date') as mock_get_start, \
             patch.object(JobHelper, '_resolve_latest_completed_trading_date', return_value='20251231'):
            
            mock_get_start.return_value = "20200101"
            
            start_date, end_date = JobHelper.calculate_start_and_end_date(
                TagUpdateMode.INCREMENTAL,
                entity_last_update_date=None,
                default_start_date="20200101",
                default_end_date="20201231"
            )
            
            assert start_date == "20200101"  # 使用默认开始日期
            assert end_date == "20201231"
