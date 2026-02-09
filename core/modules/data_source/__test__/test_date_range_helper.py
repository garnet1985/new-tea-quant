"""
date_range_helper 单元测试

覆盖几个关键入口：
- normalize_date_value
- compute_last_update_map（全局模式）
- calc_last_update_based_on_renew_mode（refresh / incremental / rolling 的基本分支）
"""

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest

    HAS_PYTEST = True
except ImportError:  # pragma: no cover
    HAS_PYTEST = False


class TestDateRangeHelper:
    def test_normalize_date_value_str_and_datetime(self):
        """简单验证 normalize_date_value 能处理常见 str / datetime 形式。"""
        from datetime import datetime
        from core.modules.data_source.service.date_range import date_range_helper as drh

        # 纯日期字符串
        v1 = drh.normalize_date_value("2024-01-02")
        assert isinstance(v1, str)
        assert v1.startswith("2024")

        # datetime 对象
        dt = datetime(2024, 1, 3, 10, 0, 0)
        v2 = drh.normalize_date_value(dt)
        assert isinstance(v2, str)
        assert v2.startswith("20240103")

    def test_compute_last_update_map_global(self):
        """
        compute_last_update_map 在非 per-entity 场景下：
        - 通过 data_manager.get_table().load_one 查出最新一条记录
        - 结果写入 {'_global': normalized_date}
        """
        from core.modules.data_source.service.date_range import date_range_helper as drh
        from core.global_enums.enums import UpdateMode

        # mock config
        config = Mock()
        config.get_table_name.return_value = "test_table"
        config.get_date_field.return_value = "date"
        config.get_date_format.return_value = "day"
        config.get_renew_mode.return_value = UpdateMode.INCREMENTAL

        # mock data_manager & model
        model = Mock()
        model.load_one.return_value = {"date": "2024-01-05"}
        data_manager = Mock()
        data_manager.get_table.return_value = model

        # 不需要 per-entity 分组
        with patch(
            "core.modules.data_source.service.date_range.date_range_helper.RenewCommonHelper.get_needs_stock_grouping",
            return_value=False,
        ):
            ctx: Dict[str, Any] = {"config": config, "data_manager": data_manager}
            last_map = drh.compute_last_update_map(ctx)

        assert "_global" in last_map
        assert isinstance(last_map["_global"], str)
        # DateUtils.normalize_str("2024-01-05") → "20240105"，这里只验证前缀
        assert last_map["_global"].startswith("20240105")

    def test_calc_last_update_refresh_uses_default_start_date(self):
        """refresh 模式应直接使用 RenewCommonHelper.get_default_date_range 返回的起点。"""
        from core.modules.data_source.service.date_range import date_range_helper as drh
        from core.global_enums.enums import UpdateMode

        config = Mock()
        config.get_renew_mode.return_value = UpdateMode.REFRESH
        config.get_date_format.return_value = "day"

        ctx = {"config": config, "data_manager": Mock()}

        with patch(
            "core.modules.data_source.service.date_range.date_range_helper.RenewCommonHelper.get_default_date_range",
            return_value=("20000101", "20001231"),
        ):
            start = drh.calc_last_update_based_on_renew_mode(ctx, last_update="20240101")

        assert start == "20000101"

    def test_calc_last_update_incremental_from_last_update_plus_one(self):
        """
        incremental 模式：
        - 当有 last_update 时，应该从 last_update 的后一个周期开始。
        这里通过 patch DateUtils 保证行为可预测。
        """
        from core.modules.data_source.service.date_range import date_range_helper as drh
        from core.global_enums.enums import UpdateMode

        config = Mock()
        config.get_renew_mode.return_value = UpdateMode.INCREMENTAL
        config.get_date_format.return_value = "day"

        ctx = {"config": config, "data_manager": Mock()}

        with patch(
            "core.modules.data_source.service.date_range.date_range_helper.RenewCommonHelper.get_default_date_range",
            return_value=("19990101", "19990102"),
        ), patch(
            "core.modules.data_source.service.date_range.date_range_helper.DateUtils"
        ) as MockDU:
            MockDU.normalize_period_type.return_value = "day"

            # last_update="20240101" → add_periods(...,1,"day") 返回 "20240102"
            MockDU.add_periods.return_value = "20240102"
            MockDU.from_period_str.return_value = "2024-01-02"

            start = drh.calc_last_update_based_on_renew_mode(
                ctx,
                last_update="20240101",
            )

        assert start == "2024-01-02"


if __name__ == "__main__":  # pragma: no cover
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        test = TestDateRangeHelper()
        for name in [
            "test_normalize_date_value_str_and_datetime",
            "test_compute_last_update_map_global",
            "test_calc_last_update_refresh_uses_default_start_date",
            "test_calc_last_update_incremental_from_last_update_plus_one",
        ]:
            try:
                getattr(test, name)()
                print(f"✅ {name} 通过")
            except Exception as e:
                print(f"❌ {name} 失败: {e}")

