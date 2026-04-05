"""
fetched_data_helper 单元测试

覆盖：
- build_grouped_fetched_data（单字段 / 多字段分组）
- build_unified_fetched_data
- has_group_by_config

实现依赖强类型 `DataSourceConfig`（与 executor 一致），不再使用 Mock 冒充 config。
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest

    HAS_PYTEST = True
except ImportError:  # pragma: no cover
    HAS_PYTEST = False

from core.modules.data_source.data_class.config import DataSourceConfig


def _api(params_mapping: Dict[str, str]) -> Dict[str, Any]:
    return {
        "provider_name": "p",
        "method": "m",
        "max_per_minute": 60,
        "params_mapping": params_mapping,
    }


def _ds_config(
    apis: Dict[str, Dict[str, Any]],
    *,
    with_job_execution: bool = True,
) -> DataSourceConfig:
    renew: Dict[str, Any] = {"type": "refresh"}
    if with_job_execution:
        renew["job_execution"] = {"list": "stocks", "key": "id"}
    raw = {
        "table": "t_test",
        "save_mode": "batch",
        "renew": renew,
        "apis": apis,
    }
    return DataSourceConfig.from_dict(raw, "test_ds")


class TestFetchedDataHelper:
    def test_build_grouped_fetched_data_single_field(self):
        """单字段 params_mapping：entity_id 直接来自 params[param_key]。"""
        from core.modules.data_source.service.executor import fetched_data_helper as fd
        from core.modules.data_source.data_class.api_job import ApiJob

        cfg = _ds_config({"api1": _api({"id": "id"})})
        context = {"config": cfg, "data_source_key": "test_ds"}

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
        """多字段 params_mapping：entity_id 用 '::' 按 params_mapping 的 key 顺序拼接 params。"""
        from core.modules.data_source.service.executor import fetched_data_helper as fd
        from core.modules.data_source.data_class.api_job import ApiJob

        cfg = _ds_config({"api1": _api({"id": "id", "term": "term"})})
        context = {"config": cfg, "data_source_key": "test_ds"}

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

        assert grouped["api1"] == {"000001::daily": "result1"}

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
        """有 job_execution 且存在带 params_mapping 的 API 时 True；否则 False。"""
        from core.modules.data_source.service.executor import fetched_data_helper as fd
        from core.modules.data_source.data_class.api_job import ApiJob

        cfg_true = _ds_config(
            {
                "api1": _api({"id": "id"}),
                "api2": _api({}),
            },
            with_job_execution=True,
        )
        apis = [
            ApiJob(api_name="api1", provider_name="p", method="m"),
            ApiJob(api_name="api2", provider_name="p", method="m"),
        ]
        assert fd.has_group_by_config({"config": cfg_true}, apis) is True

        cfg_false = _ds_config(
            {
                "api1": _api({"id": "id"}),
                "api2": _api({}),
            },
            with_job_execution=False,
        )
        assert fd.has_group_by_config({"config": cfg_false}, apis) is False


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
