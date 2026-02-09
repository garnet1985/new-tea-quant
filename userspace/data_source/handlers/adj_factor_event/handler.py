"""
复权因子事件 Handler

使用框架标准流程：preprocess → executing → postprocess → save。
每股拉取 adj_factor + daily_kline + qfq_kline，在 on_after_single_api_job_bundle_complete 中 build + save。
"""
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import os
import pandas as pd

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.config import DataSourceConfig
from userspace.data_source.handlers.adj_factor_event.helper import AdjFactorEventHandlerHelper as helper
from core.infra.project_context import ConfigManager


class AdjFactorEventHandler(BaseHandler):
    """
    复权因子事件 Handler

    使用框架：每股一个 bundle（adj_factor + daily_kline + qfq_kline），
    每个 bundle 完成后在 on_after_single_api_job_bundle_complete 中 build + save。
    """

    def __init__(
        self,
        data_source_key: str,
        schema,
        config: DataSourceConfig,
        providers: Dict[str, BaseProvider],
        depend_on_data_source_names: List[str] = None,
    ):
        super().__init__(data_source_key, schema, config, providers, depend_on_data_source_names or [])

    def on_build_job_payload(
        self,
        entity_info: Any,
        apis: List[ApiJob],
        context: Dict[str, Any],
    ) -> Optional[str]:
        """注入 ts_code/symbol、日期范围。"""
        entity_id = entity_info.get("id") if isinstance(entity_info, dict) else str(entity_info)
        if not entity_id:
            return None

        latest = context.get("latest_completed_trading_date")
        default_start = ConfigManager.get_default_start_date()

        for job in apis:
            job.params = job.params or {}
            if job.api_name == "qfq_kline":
                job.params["symbol"] = helper.convert_to_tx_symbol(str(entity_id))
            else:
                job.params["ts_code"] = str(entity_id)
            job.params["start_date"] = default_start
            job.params["end_date"] = latest

        return str(entity_id)

    def on_after_single_api_job_bundle_complete(
        self, context: Dict[str, Any], job_bundle: ApiJobBundle, fetched_data: Dict[str, Any]
    ) -> None:
        """每股请求完成后：build adj_factor_events → delete + save。"""
        stock_id = self._extract_stock_id(job_bundle)
        if not stock_id:
            return

        if context.get("is_dry_run"):
            return

        adj_df = fetched_data.get("adj_factor")
        daily_df = fetched_data.get("daily_kline")
        qfq_result = fetched_data.get("qfq_kline")

        if adj_df is None or (isinstance(adj_df, pd.DataFrame) and adj_df.empty):
            logger.warning(f"⚠️ [{stock_id}] adj_factor 为空，跳过")
            return

        if daily_df is None or (isinstance(daily_df, pd.DataFrame) and daily_df.empty):
            logger.warning(f"⚠️ [{stock_id}] daily_kline 为空，跳过")
            return

        # qfq_kline 仅来自 AKShare，失败时为 None
        if isinstance(qfq_result, pd.DataFrame):
            qfq_price_map = helper.parse_akshare_qfq_price_map(qfq_result)
        else:
            qfq_price_map = {}

        if not qfq_price_map:
            logger.warning(f"⚠️ [{stock_id}] 前复权解析后为空，跳过")
            return

        raw_price_map = helper.build_raw_price_map(daily_df)
        first_kline_ymd = min(qfq_price_map.keys()) if qfq_price_map else None
        if not first_kline_ymd and isinstance(daily_df, pd.DataFrame) and "trade_date" in daily_df.columns:
            first_kline_ymd = helper.normalize_date_to_yyyymmdd(str(daily_df["trade_date"].min()))

        if not first_kline_ymd:
            logger.warning(f"⚠️ [{stock_id}] 无第一根K线日期，跳过")
            return

        events_to_save = helper.build_adj_factor_events(
            stock_id=stock_id,
            adj_factor_df=adj_df,
            raw_price_map=raw_price_map,
            qfq_map=qfq_price_map,
            first_kline_ymd=first_kline_ymd,
        )

        if not events_to_save:
            logger.warning(f"⚠️ [{stock_id}] build_adj_factor_events 返回空，跳过")
            return

        data_manager = context["data_manager"]
        data_manager.stock.kline.delete_adj_factor_events(stock_id)
        data_manager.stock.kline.save_adj_factor_events(events_to_save)
        logger.info(f"✅ [{stock_id}] 保存 {len(events_to_save)} 个复权事件")

    def _extract_stock_id(self, job_bundle: ApiJobBundle) -> Optional[str]:
        bid = job_bundle.bundle_id or ""
        prefix = "adj_factor_event_batch_"
        if bid.startswith(prefix):
            return bid[len(prefix):]
        return None

    def on_prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """预处理：CSV 导入检查、should_generate_csv。"""
        context = super().on_prepare_context(context)
        self._latest_completed_trading_date = context.get("latest_completed_trading_date")

        data_manager = context["data_manager"]
        adj_model = data_manager.stock.kline._adj_factor_event
        context["should_generate_csv"] = False

        if hasattr(adj_model, "is_table_empty"):
            is_empty = adj_model.is_table_empty()
        else:
            try:
                is_empty = adj_model.count() == 0
            except Exception:
                return context

        if is_empty:
            if hasattr(adj_model, "get_latest_csv_file") and hasattr(adj_model, "import_from_csv"):
                if self._is_csv_exist_and_valid(adj_model):
                    cnt = adj_model.import_from_csv()
                    if cnt > 0:
                        logger.info(f"✅ 从CSV导入 {cnt} 条，表已恢复")
        else:
            if hasattr(adj_model, "get_latest_csv_file") and hasattr(adj_model, "get_current_quarter_csv_name"):
                if self._is_csv_expired(adj_model, base_date=self._latest_completed_trading_date) or not self._is_csv_exist_and_valid(adj_model):
                    context["should_generate_csv"] = True

        return context

    def _is_csv_exist_and_valid(self, adj_model) -> bool:
        if not hasattr(adj_model, "get_latest_csv_file"):
            return False
        csv_file = adj_model.get_latest_csv_file()
        if not csv_file or not os.path.exists(csv_file):
            return False
        try:
            df = pd.read_csv(csv_file, nrows=1)
            return all(c in df.columns for c in ["id", "event_date", "factor", "qfq_diff"])
        except Exception:
            return False

    def _is_csv_expired(self, adj_model, base_date: str = None) -> bool:
        if not hasattr(adj_model, "get_latest_csv_file") or not hasattr(adj_model, "get_current_quarter_csv_name"):
            return True
        csv_file = adj_model.get_latest_csv_file()
        if not csv_file:
            return True
        current_name = adj_model.get_current_quarter_csv_name(base_date=base_date)
        return os.path.basename(csv_file) != current_name

    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """immediate 模式数据已在 on_after_single_api_job_bundle_complete 保存，返回空。"""
        data_manager = context.get("data_manager")
        if data_manager and context.get("should_generate_csv"):
            adj_model = data_manager.stock.kline._adj_factor_event
            if hasattr(adj_model, "get_current_quarter_csv_name") and hasattr(adj_model, "csv_dir") and hasattr(adj_model, "export_to_csv"):
                base_date = getattr(self, "_latest_completed_trading_date", None)
                csv_name = adj_model.get_current_quarter_csv_name(base_date=base_date)
                csv_path = os.path.join(adj_model.csv_dir, csv_name)
                if not os.path.exists(csv_path):
                    exported = adj_model.export_to_csv(file_path=csv_path)
                    logger.info(f"✅ 导出季度CSV: {exported} 条 -> {csv_name}")
        return normalized_data
