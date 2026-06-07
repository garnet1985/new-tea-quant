"""collect_api_limits：限流仅从 Provider.api_limits 解析。"""
from unittest.mock import MagicMock

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.service.rate_limiter import collect_api_limits


class _FakeProvider:
    api_limits = {"get_daily_basic": 500}
    default_rate_limit = 200

    def get_api_limit(self, api_name: str):
        return self.api_limits.get(api_name, self.default_rate_limit)


def test_collect_api_limits_from_provider():
    job = ApiJob(
        api_name="daily_basic",
        provider_name="tushare",
        method="get_daily_basic",
        job_id="stock_indicators_000001.SZ",
    )
    limits = collect_api_limits([job], {"tushare": _FakeProvider()})
    assert limits["stock_indicators_000001.SZ"] == 500


def test_rejects_max_per_minute_in_handler_config():
    from core.modules.data_source.data_class.api_config import ApiConfig
    from core.modules.data_source.data_class.error import DataSourceConfigError

    try:
        ApiConfig.from_dict(
            "x",
            {"provider_name": "tushare", "method": "get_daily_basic", "max_per_minute": 500},
            "test_ds",
        )
        assert False, "expected DataSourceConfigError"
    except DataSourceConfigError as e:
        assert "max_per_minute" in str(e)
