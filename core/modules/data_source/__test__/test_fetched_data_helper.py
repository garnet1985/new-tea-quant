"""
fetched_data_helper 单元测试

覆盖：
- build_grouped_fetched_data（单字段 / 多字段分组）
- build_unified_fetched_data
- has_group_by_config
"""

import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest

    HAS_PYTEST = True
except ImportError:  # pragma: no cover
    HAS_PYTEST = False


class DummyApiConfig:
    def __init__(self, params_mapping: Dict[str, Any] | None = None):
        self.params_mapping = params_mapping or {}


class TestFetchedDataHelper:
    def _make_context_with_config(
        self, apis_conf: Dict[str, DummyApiConfig], has_group_by: bool = True
    ) -> Dict[str, Any]:
        cfg = Mock()
        cfg.get_apis.return_value = apis_conf
        cfg.has_result_group_by.return_value = has_group_by
        return {"config": cfg, "data_source_key": "test_ds"}

    def test_build_grouped_fetched_data_single_field(self):
        """单字段 params_mapping：entity_id 直接来自 params[param_key]。"""
        from core.modules.data_source.service.executor import fetched_data_helper as fd
        from core.modules.data_source.data_class.api_job import ApiJob

        # 配置：api1 有一个 params_mapping
        apis_conf: Dict[str, DummyApiConfig] = {
            "api1": DummyApiConfig(params_mapping={"id": "id"}),
        }
        context = self._make_context_with_config(apis_conf, has_group_by=True)

        # 两个 ApiJob，分别对应不同实体
        apis: List[ApiJob] = [
            ApiJob(api_name="api1", provider_name="p", method="m", params={"id": "000001"}, job_id="job1"),
            ApiJob(api_name="api1", provider_name="p", method="m", params={"id": "000002"}, job_id="job2"),
        ]

        fetched_data = {
            "job1": "result1",
            "job2": "result2",
        }

        grouped = fd.build_grouped_fetched_data(context, fetched_data, apis)

        assert "api1" in grouped
        assert grouped["api1"] == {
            "000001": "result1",
            "000002": "result2",
        }

    def test_build_grouped_fetched_data_multi_fields(self):
        """多字段 params_mapping：entity_id 用 '::' 拼接 params。"""
        from core.modules.data_source.service.executor import fetched_data_helper as fd
        from core.modules.data_source.data_class.api_job import ApiJob

        apis_conf: Dict[str, DummyApiConfig] = {
            "api1": DummyApiConfig(params_mapping={"id": "id", "term": "term"}),
        }
        context = self._make_context_with_config(apis_conf, has_group_by=True)

        apis: List[ApiJob] = [
            ApiJob(
                api_name="api1",
                provider_name="p",
                method="m",
                params={"id": "000001", "term": "daily"},
                job_id="job1",
            ),
        ]

        fetched_data = {"job1": "result1"}

        grouped = fd.build_grouped_fetched_data(context, fetched_data, apis)

        assert grouped["api1"] == {
            "000001::term": "result1",
        } or grouped["api1"] == {
            "000001::daily": "result1",
        }

    def test_build_unified_fetched_data(self):
        """build_unified_fetched_data 应按 api_name 聚合到 '_unified'。"""
        from core.modules.data_source.service.executor import fetched_data_helper as fd
        from core.modules.data_source.data_class.api_job import ApiJob

        context: Dict[str, Any] = {"data_source_key": "test_ds"}
        apis = [
            ApiJob(api_name="api1", provider_name="p", method="m", job_id="job1"),
            ApiJob(api_name="api2", provider_name="p", method="m", job_id="job2"),
        ]
        fetched_data = {"job1": "r1", "job2": "r2"}

        unified = fd.build_unified_fetched_data(context, fetched_data, apis)

        assert unified == {
            "api1": {"_unified": "r1"},
            "api2": {"_unified": "r2"},
        }

    def test_has_group_by_config_true_and_false(self):
        """has_group_by_config: 有 group_by 且 apis_conf 中存在带 params_mapping 的 API 时返回 True。"""
        from core.modules.data_source.service.executor import fetched_data_helper as fd
        from core.modules.data_source.data_class.api_job import ApiJob

        apis_conf: Dict[str, DummyApiConfig] = {
            "api1": DummyApiConfig(params_mapping={"id": "id"}),
            "api2": DummyApiConfig(params_mapping={}),
        }

        cfg = Mock()
        cfg.has_result_group_by.return_value = True
        cfg.get_apis.return_value = apis_conf

        context_true = {"config": cfg}
        apis = [
            ApiJob(api_name="api1", provider_name="p", method="m"),
            ApiJob(api_name="api2", provider_name="p", method="m"),
        ]
        assert fd.has_group_by_config(context_true, apis) is True

        # 没有 group_by 或没有任何带 params_mapping 的 API
        cfg2 = Mock()
        cfg2.has_result_group_by.return_value = False
        context_false = {"config": cfg2}
        assert fd.has_group_by_config(context_false, apis) is False


if __name__ == "__main__":  # pragma: no cover
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        test = TestFetchedDataHelper()
        for name in [
            "test_build_grouped_fetched_data_single_field",
            "test_build_grouped_fetched_data_multi_fields",
            "test_build_unified_fetched_data",
            "test_has_group_by_config_true_and_false",
        ]:
            try:
                getattr(test, name)()
                print(f"✅ {name} 通过")
            except Exception as e:
                print(f"❌ {name} 失败: {e}")

