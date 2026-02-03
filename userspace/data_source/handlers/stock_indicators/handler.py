"""
股票日度指标 Handler（stock_indicators）

从 Tushare 获取 daily_basic 数据（PE、PB、换手率、市值等），写入 sys_stock_indicators。
与 K 线 renew 分离，独立增量更新。
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.utils.date.date_utils import DateUtils
from core.infra.project_context import ConfigManager


class StockIndicatorsHandler(BaseHandler):
    """
    股票日度指标 Handler，绑定表 sys_stock_indicators。
    每个股票一个 get_daily_basic ApiJob，增量更新。
    """

    def __init__(
        self,
        data_source_key: str,
        schema,
        config,
        providers: Dict[str, BaseProvider],
        depend_on_data_source_names: List[str] = None,
    ):
        super().__init__(data_source_key, schema, config, providers, depend_on_data_source_names or [])

    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """为每只股票创建一个 get_daily_basic ApiJob。"""
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("股票列表为空，无法创建 stock_indicators 任务")
            return apis

        latest_trading_date = context.get("latest_completed_trading_date")
        if not latest_trading_date:
            data_manager = context.get("data_manager")
            if data_manager:
                try:
                    latest_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
                except Exception as e:
                    logger.warning(f"获取最新交易日失败: {e}")
            if not latest_trading_date:
                latest_trading_date = DateUtils.get_today_str()
        end_date = latest_trading_date

        stock_latest_dates = {}
        data_manager = context.get("data_manager")
        if data_manager:
            try:
                model = data_manager.get_table("sys_stock_indicators")
                if model:
                    all_latest = model.load_latests(date_field="date", group_fields=["id"])
                    for rec in all_latest or []:
                        sid = rec.get("id")
                        d = rec.get("date")
                        if sid and d:
                            stock_latest_dates[sid] = d
            except Exception as e:
                logger.warning(f"查询 sys_stock_indicators 最新日期失败: {e}")

        base_api = apis[0] if apis else None
        if not base_api:
            return apis

        expanded = []
        for stock in stock_list:
            stock_id = stock.get("ts_code") or stock.get("id")
            if not stock_id:
                continue
            latest = stock_latest_dates.get(stock_id)
            if latest:
                start_date = DateUtils.get_date_after_days(latest, 1)
                if start_date > end_date:
                    continue
            else:
                start_date = ConfigManager.get_default_start_date()
            new_api = ApiJob(
                api_name=base_api.api_name,
                provider_name=base_api.provider_name,
                method=base_api.method,
                params={
                    **base_api.params,
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                api_params=base_api.api_params,
                depends_on=base_api.depends_on,
                rate_limit=base_api.rate_limit,
                job_id=f"stock_indicators_{stock_id}",
            )
            expanded.append(new_api)
        logger.info(f"✅ 为 {len(expanded)} 只股票生成了 stock_indicators 获取任务")
        return expanded

    def on_after_fetch(self, context: Dict[str, Any], fetched_data: Dict[str, Any], apis: List[ApiJob]) -> Dict[str, Any]:
        """将 { job_id: result } 转为 { daily_basic: { stock_id: result } }，供默认 normalize 使用。"""
        unified = {"daily_basic": {}}
        prefix = "stock_indicators_"
        for job_id, result in (fetched_data or {}).items():
            if not isinstance(job_id, str) or not job_id.startswith(prefix):
                continue
            stock_id = job_id[len(prefix) :]
            if stock_id:
                unified["daily_basic"][stock_id] = result
        return unified
