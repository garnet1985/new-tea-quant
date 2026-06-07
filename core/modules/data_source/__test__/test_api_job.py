"""ApiJob 单元测试。"""
from core.modules.data_source.data_class.api_job import ApiJob


def test_init():
    job = ApiJob(
        provider_name="tushare",
        method="get_stock_list",
        params={"fields": "ts_code,name"},
    )

    assert job.provider_name == "tushare"
    assert job.method == "get_stock_list"
    assert job.params == {"fields": "ts_code,name"}
    assert job.api_name == "get_stock_list"
    assert job.depends_on == []
    assert job.rate_limit == 0


def test_post_init_api_name():
    job1 = ApiJob(provider_name="tushare", method="get_stock_list", params={})
    assert job1.api_name == "get_stock_list"

    job2 = ApiJob(
        provider_name="tushare",
        method="get_stock_list",
        params={},
        api_name="custom_api_name",
    )
    assert job2.api_name == "custom_api_name"


def test_depends_on():
    job = ApiJob(
        provider_name="tushare",
        method="get_daily_kline",
        params={},
        depends_on=["job1", "job2"],
    )
    assert job.depends_on == ["job1", "job2"]
