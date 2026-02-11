from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging

from core.global_enums.enums import UpdateMode
from core.infra.project_context import ConfigManager
from core.modules.data_source.data_class.api_config import ApiConfig
from core.modules.data_source.data_class.api_job import ApiJob
from core.utils.utils import Utils
from core.modules.data_source.service.normalization import normalization_helper as nh
from core.modules.data_source.service.executor import fetched_data_helper as fd
from core.modules.data_source.service.date_range import date_range_helper as drh


logger = logging.getLogger(__name__)


class DataSourceHandlerHelper:
    """
    DataSource Handler 侧的辅助方法

    目标：
    - 将 config 中的 apis 转换为 ApiJob 列表；
    - 提供基于 result_mapping / schema 的默认标准化实现；
    - 具体细节都收敛在这里，BaseHandler 中只保留“步骤大纲”。
    """

    # ========== ApiJob 构造 ==========

    @staticmethod
    def build_api_jobs(apis: Dict[str, ApiConfig]) -> List[ApiJob]:
        """
        将 config 中的 apis 定义转换为 ApiJob 列表。

        apis: Dict[str, ApiConfig]，来自 DataSourceConfig.get_apis()
        """
        jobs: List[ApiJob] = []

        if not apis:
            return jobs

        for api_name, api_cfg in apis.items():
            job = ApiJob(
                api_name=api_name,
                provider_name=api_cfg.provider_name,
                method=api_cfg.method,
                params=api_cfg.params,
                api_params={
                    "params_mapping": api_cfg.params_mapping,
                    "result_mapping": api_cfg.result_mapping,
                    **api_cfg.params,
                },
                depends_on=[],
                rate_limit=api_cfg.max_per_minute,
                job_id=api_name,
            )
            jobs.append(job)

        return jobs

    # ========== 日期范围 & renew_mode ==========

    @staticmethod
    def ensure_date_range(context: Dict[str, Any]) -> None:
        """
        根据 config 中的 renew_mode / default_date_range，在 context 中补全 start_date / end_date。

        设计目标：
        - 如果调用方已经在 context 中显式给出了 start_date / end_date，则不做修改；
        - 否则根据 renew_mode + default_date_range 给出一个“合理的默认范围”（不访问数据库）；
        - 复杂的增量 / 滚动逻辑交给上层或专用服务覆盖。

        当前简化策略：
        - 支持的 date_format：day / date / month / quarter / none（不区分大小写，默认 day）；
        - default_date_range: {"years": N}，表示从 N 年前到今天；
        - 不涉及数据库，仅基于当前日期计算。
        """
        if context is None:
            return

        # 已经有日期范围则不干预
        if "start_date" in context and "end_date" in context:
            return

        from core.modules.data_source.data_class.config import DataSourceConfig

        config = context.get("config")
        if not isinstance(config, DataSourceConfig):
            return
        renew_mode = config.get_renew_mode().value
        date_format = config.get_date_format().lower()
        years = config.get_default_date_range_years()

        from datetime import datetime, timedelta

        today = datetime.today()
        if date_format in ("day", "date"):
            end = today
            start = today - timedelta(days=365 * years)
            fmt = "%Y-%m-%d"
        elif date_format == "month":
            # 简化：按 30 天一月估算
            end = today
            start = today - timedelta(days=30 * 12 * years)
            fmt = "%Y-%m"
        elif date_format == "quarter":
            # 简化：按 3 个月一季度估算，用 YYYYQn 表示
            year = today.year
            quarter = (today.month - 1) // 3 + 1
            end_str = f"{year}Q{quarter}"
            start_year = year - years
            start_str = f"{start_year}Q1"
            context["start_date"] = start_str
            context["end_date"] = end_str
            logger.info(
                f"📅 自动设置季度范围: {start_str} → {end_str} "
                f"(renew_mode={renew_mode or 'unknown'})"
            )
            return
        else:
            # 不识别的 format 或 none，不设置日期
            logger.info(f"日期格式 {date_format} 不支持自动范围计算，跳过 ensure_date_range")
            return

        start_str = start.strftime(fmt)
        end_str = end.strftime(fmt)
        context["start_date"] = start_str
        context["end_date"] = end_str
        logger.info(
            f"📅 自动设置日期范围: {start_str} → {end_str} "
            f"(renew_mode={renew_mode or 'unknown'}, years={years})"
        )

    @staticmethod
    def is_date_range_specified(context: Dict[str, Any]) -> bool:
        """
        判断 context 中是否已经显式指定了 start_date / end_date。
        """
        if not context:
            return False
        return "start_date" in context and "end_date" in context


    @staticmethod
    def add_date_range(
        apis: List[ApiJob],
        start_date: Any,
        end_date: Any,
        per_stock_date_ranges: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> List[ApiJob]:
        """
        将 start_date / end_date 注入到每个 ApiJob 的 params 中。

        约定：
        - 各 API 对 start_date / end_date 的具体含义由各自的 provider/handler 决定；
        - 此处只做通用注入，子类可以覆盖或在 on_before_fetch 中进一步细化。
        
        Args:
            apis: ApiJob 列表
            start_date: 统一的起始日期（当 per_stock_date_ranges 为 None 时使用）
            end_date: 统一的结束日期（当 per_stock_date_ranges 为 None 时使用）
            per_stock_date_ranges: per stock 的日期范围字典 {stock_id: (start_date, end_date)}
        
        Returns:
            List[ApiJob]: 已注入日期范围的 ApiJob 列表
        """
        if per_stock_date_ranges:
            # per stock 模式：从 ApiJob 的 params 中按 params_mapping 提取 entity_id
            for job in apis or []:
                params = job.params or {}
                params_mapping = getattr(job, "api_params", None) or {}
                params_mapping = params_mapping.get("params_mapping") or {}

                stock_id = None
                if params_mapping:
                    entity_to_param = {v: k for k, v in params_mapping.items()}
                    if len(entity_to_param) == 1:
                        param_key = next(iter(entity_to_param.values()))
                        stock_id = params.get(param_key)
                    else:
                        parts = [
                            str(params.get(entity_to_param[ef], ""))
                            for ef in sorted(entity_to_param.keys())
                        ]
                        stock_id = "::".join(parts) if parts and any(parts) else None
                
                if stock_id:
                    stock_id_str = str(stock_id)
                    date_range = per_stock_date_ranges.get(stock_id_str)
                    if date_range:
                        job_start_date, job_end_date = date_range
                        if job_start_date is not None:
                            params.setdefault("start_date", job_start_date)
                        if job_end_date is not None:
                            params.setdefault("end_date", job_end_date)
                    else:
                        # 如果找不到对应的日期范围，使用统一的日期范围（降级）
                        logger.warning(f"股票 {stock_id_str} 在 per_stock_date_ranges 中未找到，使用统一日期范围")
                        if start_date is not None:
                            params.setdefault("start_date", start_date)
                        if end_date is not None:
                            params.setdefault("end_date", end_date)
                else:
                    # 如果无法提取 stock_id，使用统一的日期范围（降级）
                    logger.warning(f"ApiJob {job.job_id} 无法提取 stock_id，使用统一日期范围")
                    if start_date is not None:
                        params.setdefault("start_date", start_date)
                    if end_date is not None:
                        params.setdefault("end_date", end_date)
                
                job.params = params
        else:
            # 统一模式：所有 ApiJob 使用相同的日期范围
            for job in apis or []:
                params = job.params or {}
                if start_date is not None:
                    params.setdefault("start_date", start_date)
                if end_date is not None:
                    params.setdefault("end_date", end_date)
                job.params = params
        
        return apis

    # ================================
    # 通用字段/日期/NaN 处理工具
    # ================================

    @staticmethod
    def add_constant_fields(
        records: List[Dict[str, Any]],
        **fields: Any,
    ) -> List[Dict[str, Any]]:
        """
        在一批记录上追加固定字段（原地修改并返回）。
        """
        if not records or not fields:
            return records
        for r in records:
            if isinstance(r, dict):
                r.update(fields)
        return records

    # 后续通用的日期标准化、NaN 清洗和标准化入口已经迁移到
    # normalization_helper / record_utils 中，这里不再保留代理方法。

    # ================================
    # Renew 辅助：一次性获取所有实体的 last_update 映射
    # ================================

    @staticmethod
    def get_last_update_map(
        context: Dict[str, Any],
        renew_mode: UpdateMode,
    ) -> Dict[str, Optional[str]]:
        """
        获取所有实体的“本次抓取起点”映射。

        语义：
        - REFRESH:   不查 DB，所有实体统一从全局 default_start_date 开始；
        - 其他模式:  一次性从 DB 查询原始 latest_date，再根据 renew_mode 计算起点。
        """
        # per-entity 的实体列表（例如 dependencies["entity_list"]）
        deps = context.get("dependencies") or {}
        entity_list = deps.get("entity_list")

        if renew_mode == UpdateMode.REFRESH:
            if not entity_list:
                return {}
            default_start = ConfigManager.get_default_start_date()
            return {str(entity_id): default_start for entity_id in entity_list}

        # 非 refresh：统一查一次 DB，拿到原始 last_update，再按模式转换为“起点”
        raw_last_update_map = drh.compute_last_update_map(context)
        result: Dict[str, Optional[str]] = {}

        if entity_list:
            for entity_id in entity_list:
                key = str(entity_id)
                raw_last = raw_last_update_map.get(key)
                start_date = drh.calc_last_update_based_on_renew_mode(
                    context, entity_id=key, last_update=raw_last
                )
                result[key] = start_date
        else:
            # 没有显式 entity_list，就直接对 DB 返回的 key 做转换
            for key, raw_last in raw_last_update_map.items():
                start_date = drh.calc_last_update_based_on_renew_mode(
                    context, entity_id=str(key), last_update=raw_last
                )
                result[str(key)] = start_date

        return result

    @staticmethod
    def get_last_update(
        context: Dict[str, Any],
        renew_mode: UpdateMode,
    ) -> Optional[str]:
        """
        获取“单实体/全局”的本次抓取起点日期。

        - REFRESH:   直接使用全局 default_start_date；
        - 其他模式:  从 DB 查询当前数据源的最新日期，再根据 renew_mode 计算本次起点。
        """
        if renew_mode == UpdateMode.REFRESH:
            return ConfigManager.get_default_start_date()

        # 使用 compute_last_update_map 的全局分支（"_global"）获取原始 last_update
        raw_map = drh.compute_last_update_map(context)
        raw_last = raw_map.get("_global")
        return drh.calc_last_update_based_on_renew_mode(
            context, entity_id=None, last_update=raw_last
        )


    @staticmethod
    def _get_last_trading_date_before(
        data_manager,
        target_date: str,
        latest_completed_trading_date: str,
        max_days_back: int = 7
    ) -> str:
        """
        找到指定日期之前的最后一个交易日。
        
        用于周线和月线的end_date计算，避免获取未完成周期的数据。
        
        Args:
            data_manager: DataManager实例
            target_date: 目标日期（YYYYMMDD格式），要找这个日期之前的最后一个交易日
            latest_completed_trading_date: 最新已完成交易日（作为上限，不会超过这个日期）
            max_days_back: 最多往前查找的天数（防止无限循环，默认7天足够）
        
        Returns:
            最后一个交易日（YYYYMMDD格式），如果找不到则返回target_date
        """
        from core.utils.date.date_utils import DateUtils
        from datetime import datetime, timedelta
        
        # 确保不超过latest_completed_trading_date
        if DateUtils.is_after(target_date, latest_completed_trading_date):
            target_date = latest_completed_trading_date
        
        # 简单往前查找：从target_date开始往前找，最多找max_days_back天
        # A股的周交易日：周一到周五通常是交易日，周日也可能是交易日（特殊情况下）
        current_date = datetime.strptime(target_date, "%Y%m%d")
        for i in range(max_days_back):
            check_date = current_date - timedelta(days=i)
            check_date_str = check_date.strftime("%Y%m%d")
            
            # 确保不超过latest_completed_trading_date
            if DateUtils.is_after(check_date_str, latest_completed_trading_date):
                continue
            
            # 判断：周一到周五是交易日，周日也可能是交易日（A股的周交易日最后一天是周日）
            weekday = check_date.weekday()  # 0=Monday, 6=Sunday
            if weekday < 5 or weekday == 6:  # 周一到周五，或周日
                return check_date_str
        
        # 如果都找不到，返回target_date（保守策略）
        return target_date

    # 其他基于 last_update 的日期范围计算、跨天数阈值判断等逻辑已经迁移到
    # date_range_helper / date_range_service 中，这里不再保留代理方法。

