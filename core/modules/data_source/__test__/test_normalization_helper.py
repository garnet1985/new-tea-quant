"""
normalization_helper 单元测试

覆盖核心工具函数：
- result_to_records
- apply_schema / build_normalized_payload
- validate_normalized_data
- normalize_date_field
"""

import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

# 添加项目根目录到路径（与现有 UT 风格保持一致）
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest

    HAS_PYTEST = True
except ImportError:  # pragma: no cover
    HAS_PYTEST = False


class TestNormalizationHelper:
    """normalization_helper 测试类"""

    def test_result_to_records_with_dataframe_like(self):
        """当传入具有 to_dict('records') 的对象时，应调用该方法并返回结果。"""
        from core.modules.data_source.service.normalization import normalization_helper as nh

        class FakeDataFrame:
            def __init__(self, records: List[Dict[str, Any]]):
                self._records = records

            def to_dict(self, orient: str):
                assert orient == "records"
                return self._records

        records = [{"id": 1}, {"id": 2}]
        df = FakeDataFrame(records)

        result = nh.result_to_records(df)
        assert result == records

    def test_result_to_records_with_list_of_dict(self):
        """当传入 list[dict] 时，应直接返回。"""
        from core.modules.data_source.service.normalization import normalization_helper as nh

        records = [{"id": 1}, {"id": 2}]
        result = nh.result_to_records(records)
        assert result is records

    def test_apply_schema_and_build_normalized_payload(self):
        """验证 apply_schema 做类型转换并只保留 schema 字段，build_normalized_payload 包装为 {'data': [...]}。"""
        from core.modules.data_source.service.normalization import normalization_helper as nh

        schema = {
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "value", "type": "float"},
                {"name": "name", "type": "varchar"},
            ]
        }
        records = [
            {"id": "1", "value": "3.14", "name": "foo", "extra": "x"},
            {"id": "2", "value": None, "name": "bar"},
        ]

        normalized = nh.apply_schema(records, schema)
        assert normalized == [
            {"id": 1, "value": 3.14, "name": "foo"},
            {"id": 2, "value": None, "name": "bar"},
        ]

        payload = nh.build_normalized_payload(normalized)
        assert payload == {"data": normalized}

    def test_validate_normalized_data_success_and_failure(self):
        """validate_normalized_data 在数据符合 schema 时静默通过，违规时抛出异常。"""
        from core.modules.data_source.service.normalization import normalization_helper as nh

        schema = {
            "fields": [
                {"name": "id", "type": "int", "isRequired": True},
                {"name": "name", "type": "varchar", "isRequired": True},
            ]
        }

        ok_payload = {"data": [{"id": 1, "name": "foo"}]}
        # 不应抛出异常
        nh.validate_normalized_data(ok_payload, schema, data_source_key="test_ok")

        bad_payload = {"data": [{"id": "not_int", "name": "foo"}]}
        with pytest.raises(ValueError):
            nh.validate_normalized_data(bad_payload, schema, data_source_key="test_bad")

    def test_normalize_date_field_uses_dateutils_and_updates_records(self):
        """
        normalize_date_field 应调用 DateUtils.normalize_period_value，
        并将返回值写回记录。
        """
        from core.modules.data_source.service.normalization import normalization_helper as nh

        records = [
            {"date": "2024-01-02", "v": 1},
            {"date": "2024/01/03", "v": 2},
            {"no_date": "x"},
        ]

        # patch DateUtils 以避免依赖真实实现（patch 到实际导入位置）
        with patch("core.utils.date.date_utils.DateUtils") as MockDateUtils:
            MockDateUtils.PERIOD_DAY = "day"

            def fake_normalize_period_type(fmt: str) -> str:
                assert fmt in ("day", "date")
                return "day"

            MockDateUtils.normalize_period_type.side_effect = fake_normalize_period_type

            def fake_normalize_period_value(value: Any, period: str) -> str:
                # 简单拼接方便断言
                return f"norm:{value}"

            MockDateUtils.normalize_period_value.side_effect = fake_normalize_period_value

            out = nh.normalize_date_field(records, field="date", target_format="day")

        # 返回同一个列表对象，原地修改
        assert out is records
        assert records[0]["date"] == "norm:2024-01-02"
        assert records[1]["date"] == "norm:2024/01/03"
        # 没有 date 字段的记录保持不变
        assert "date" not in records[2]


if __name__ == "__main__":  # pragma: no cover
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        test = TestNormalizationHelper()
        for name in [
            "test_result_to_records_with_dataframe_like",
            "test_result_to_records_with_list_of_dict",
            "test_apply_schema_and_build_normalized_payload",
            "test_validate_normalized_data_success_and_failure",
            "test_normalize_date_field_uses_dateutils_and_updates_records",
        ]:
            try:
                getattr(test, name)()
                print(f"✅ {name} 通过")
            except Exception as e:
                print(f"❌ {name} 失败: {e}")

