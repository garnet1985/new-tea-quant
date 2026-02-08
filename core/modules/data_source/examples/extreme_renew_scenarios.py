"""
极端 Renew 场景示例

展示如何使用 on_calculate_date_range 钩子实现复杂的 renew 机制。
"""
from typing import Dict, Any, Tuple, Optional, Union, List
from datetime import datetime, timedelta
from loguru import logger
import random

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.data_class.api_job import ApiJob
from core.utils.date.date_utils import DateUtils


# ============================================================================
# 场景 1: Corporate Finance Renew
# ============================================================================

class CorporateFinanceHandler(BaseHandler):
    """
    Corporate Finance 数据源 Handler
    
    需求：
    1. 需要抽样rolling，更新2个季度的数据，每次抽样500个股票更新
    2. 每年的季度分界点的后一个月需要全量更新（每年4月7月10月和1月）
    
    实现策略：
    - 在 on_calculate_date_range 中判断是否需要抽样，并将抽样的股票列表存储到 context
    - 在 on_before_fetch 中过滤 ApiJobs，只保留抽样股票的 ApiJobs
    - 注意：如果 ApiJobs 是在 _preprocess 阶段基于 stock_list 构建的，需要在构建前修改 stock_list
    """
    
    def _preprocess(self, global_dependencies: Dict[str, Any]) -> List[ApiJob]:
        """
        覆盖 _preprocess 方法，在构建 ApiJobs 之前进行股票抽样
        
        注意：这是一个更早的钩子，可以在构建 ApiJobs 之前修改 stock_list
        """
        # 注入全局依赖
        self.context = self._inject_required_global_dependencies(global_dependencies)
        
        # 判断是否需要抽样
        current_date = DateUtils.today()
        current_month = int(current_date[4:6])
        is_quarter_boundary_month = current_month in [1, 4, 7, 10]
        
        stock_list = self.context.get("stock_list", [])
        if stock_list and not is_quarter_boundary_month:
            # 非季度分界点月份：抽样500个股票
            sample_size = min(500, len(stock_list))
            sampled_stocks = random.sample(stock_list, sample_size)
            logger.info(f"非季度分界点月份，抽样 {sample_size} 只股票（共 {len(stock_list)} 只）")
            # 修改 context 中的 stock_list（注意：这里修改的是 self.context，不是传入的 global_dependencies）
            self.context["stock_list"] = sampled_stocks
            self.context["_is_sampled"] = True
        else:
            self.context["_is_sampled"] = False
        
        # 继续父类的 _preprocess 流程（构建 ApiJobs）
        # 注意：如果子类需要自定义 ApiJobs 构建逻辑，可以覆盖 _config_to_api_jobs 方法
        apis_jobs = self._config_to_api_jobs()
        
        # 注入日期范围
        apis_jobs = self._add_date_range_to_api_jobs(self.context, apis_jobs)
        
        return apis_jobs
    
    def on_calculate_date_range(
        self, 
        context: Dict[str, Any], 
        apis: List[ApiJob]
    ) -> Optional[Union[Tuple[str, str], Dict[str, Tuple[str, str]]]]:
        """
        实现复杂的日期范围计算逻辑：
        - 判断是否是季度分界点的后一个月（4月、7月、10月、1月）
        - 如果是：全量更新所有股票
        - 如果不是：使用抽样后的股票列表进行rolling更新
        """
        # 获取当前日期
        current_date = DateUtils.today()
        current_month = int(current_date[4:6])
        
        # 判断是否是季度分界点的后一个月（4月、7月、10月、1月）
        is_quarter_boundary_month = current_month in [1, 4, 7, 10]
        
        # 获取股票列表（可能已经被抽样）
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("stock_list 为空，无法进行更新")
            return None
        
        # 获取结束日期（latest_completed_trading_date）
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            logger.warning("latest_completed_trading_date 为空，使用当前日期")
            latest_completed_trading_date = current_date
        
        # 计算2个季度的rolling日期范围
        period_type = DateUtils.PERIOD_QUARTER
        end_period = DateUtils.to_period_str(latest_completed_trading_date, period_type)
        start_period = DateUtils.sub_periods(end_period, 2, period_type)
        start_date = DateUtils.from_period_str(start_period, period_type, is_start=True)
        end_date = DateUtils.from_period_str(end_period, period_type, is_start=True)
        
        # 为所有股票返回相同的日期范围（2个季度）
        logger.info(f"{'季度分界点月份' if is_quarter_boundary_month else '抽样'}更新 {len(stock_list)} 只股票，日期范围: {start_date} 至 {end_date}")
        result = {}
        for stock_id in stock_list:
            result[str(stock_id)] = (start_date, end_date)
        return result


# ============================================================================
# 场景 2: GDP 更新
# ============================================================================

class GDPHandler(BaseHandler):
    """
    GDP 数据源 Handler
    
    需求：
    - 是quarter为单位，每次rolling 2个quarter
    - 不需要按股票分组（GDP是宏观数据）
    """
    
    def on_calculate_date_range(
        self, 
        context: Dict[str, Any], 
        apis: List[ApiJob]
    ) -> Optional[Union[Tuple[str, str], Dict[str, Tuple[str, str]]]]:
        """
        实现 GDP 的 rolling 更新逻辑：
        - 每次rolling 2个quarter
        - 返回单个日期范围（不需要 per stock）
        """
        # 获取结束日期
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            latest_completed_trading_date = DateUtils.today()
        
        # 计算2个季度的rolling日期范围
        period_type = DateUtils.PERIOD_QUARTER
        end_period = DateUtils.to_period_str(latest_completed_trading_date, period_type)
        start_period = DateUtils.sub_periods(end_period, 2, period_type)
        start_date = DateUtils.from_period_str(start_period, period_type, is_start=True)
        end_date = DateUtils.from_period_str(end_period, period_type, is_start=True)
        
        logger.info(f"GDP rolling 更新: {start_date} 至 {end_date}（2个季度）")
        return (start_date, end_date)
        
        # 注意：也可以返回 None，使用默认的 RollingRenewService
        # 但需要确保配置中设置了 rolling_unit="quarter", rolling_length=2


# ============================================================================
# 场景 3: 股票K线具体信息更新（基于数据质量检查）
# ============================================================================

class StockKlineQualityHandler(BaseHandler):
    """
    股票K线数据源 Handler（基于数据质量检查）
    
    需求：
    1. 扫描股票里某些特定值为0，就需要从最早出现0的日期开始更新的数据库的最后一个数据位置
    2. 这种更新间隔不小于7天
    """
    
    def on_calculate_date_range(
        self, 
        context: Dict[str, Any], 
        apis: List[ApiJob]
    ) -> Optional[Union[Tuple[str, str], Dict[str, Tuple[str, str]]]]:
        """
        实现基于数据质量检查的日期范围计算：
        1. 查询数据库，找到值为0的记录
        2. 计算每个股票最早出现0的日期
        3. 检查上次更新时间，确保间隔不小于7天
        4. 返回per stock的日期范围
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("data_manager 为空，无法查询数据库")
            return None
        
        config = context.get("config")
        if not config:
            logger.warning("config 为空，无法获取表名和字段信息")
            return None
        
        from core.modules.data_source.data_class.config import DataSourceConfig

        if not isinstance(config, DataSourceConfig):
            logger.warning("config 必须为 DataSourceConfig 实例")
            return None
        table_name = config.get_table_name()
        date_field = config.get_date_field()
        quality_field = "volume"  # 示例：检查 volume 字段是否为0
        
        if not table_name or not date_field:
            logger.warning("table_name 或 date_field 为空")
            return None
        
        # 获取股票列表
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("stock_list 为空")
            return None
        
        # 获取结束日期
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            latest_completed_trading_date = DateUtils.today()
        
        # 获取上次更新时间（从 context 或数据库查询）
        last_update_time = context.get("_last_update_time")
        if not last_update_time:
            # 可以从数据库查询上次更新时间，这里简化处理
            last_update_time = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        # 检查更新间隔是否不小于7天
        last_update_dt = datetime.strptime(last_update_time, "%Y%m%d")
        current_dt = datetime.strptime(latest_completed_trading_date, "%Y%m%d")
        days_since_last_update = (current_dt - last_update_dt).days
        
        if days_since_last_update < 7:
            logger.info(f"距离上次更新仅 {days_since_last_update} 天，小于7天，跳过更新")
            return {}  # 返回空字典，表示不需要更新
        
        try:
            # 获取表的 model
            model = data_manager.get_table(table_name)
            if not model:
                logger.warning(f"无法获取表 {table_name} 的 model")
                return None
            
            # 查询每个股票最早出现0的日期
            result = {}
            for stock_id in stock_list:
                stock_id_str = str(stock_id)
                
                # 查询该股票中 quality_field 为0的最早记录
                # 这里使用简化的查询逻辑，实际应该使用 model 的查询方法
                try:
                    # 示例查询：SELECT MIN(date_field) FROM table WHERE id=stock_id AND quality_field=0
                    # 实际实现需要根据具体的 model API
                    earliest_zero_date = self._find_earliest_zero_date(
                        model, stock_id_str, date_field, quality_field
                    )
                    
                    if earliest_zero_date:
                        # 找到了值为0的记录，从最早出现0的日期开始更新
                        start_date = earliest_zero_date
                        end_date = latest_completed_trading_date
                        result[stock_id_str] = (start_date, end_date)
                        logger.debug(f"股票 {stock_id_str} 发现数据质量问题，从 {start_date} 开始更新")
                    else:
                        # 没有找到值为0的记录，不需要更新
                        logger.debug(f"股票 {stock_id_str} 未发现数据质量问题，跳过")
                except Exception as e:
                    logger.warning(f"查询股票 {stock_id_str} 的数据质量失败: {e}")
                    continue
            
            logger.info(f"数据质量检查完成，发现 {len(result)} 只股票需要更新")
            return result
            
        except Exception as e:
            logger.error(f"数据质量检查失败: {e}")
            return None
    
    def _find_earliest_zero_date(
        self, 
        model, 
        stock_id: str, 
        date_field: str, 
        quality_field: str
    ) -> Optional[str]:
        """
        查找股票中 quality_field 为0的最早日期
        
        实际实现需要根据具体的 model API 进行查询
        """
        try:
            # 示例：使用 model 的查询方法
            # 实际实现需要根据具体的 ORM 或查询接口
            # 这里只是示例，实际应该使用 model.load() 或类似的查询方法
            
            # 假设 model 有类似这样的查询方法：
            # records = model.load(f"id='{stock_id}' AND {quality_field}=0", order_by=f"{date_field} ASC", limit=1)
            # if records:
            #     return records[0].get(date_field)
            
            # 简化示例：返回 None 表示未找到
            return None
        except Exception as e:
            logger.warning(f"查询最早0值日期失败: {e}")
            return None


# ============================================================================
# 场景 2 的替代实现（使用默认 RollingRenewService）
# ============================================================================

class GDPHandlerSimple(BaseHandler):
    """
    GDP 数据源 Handler（简化版，使用默认逻辑）
    
    如果配置中设置了：
    - renew_mode: "rolling"
    - rolling_unit: "quarter"
    - rolling_length: 2
    - needs_stock_grouping: false
    
    则可以直接使用默认的 RollingRenewService，不需要覆盖钩子
    """
    
    # 不需要覆盖 on_calculate_date_range，直接使用默认逻辑
    pass
