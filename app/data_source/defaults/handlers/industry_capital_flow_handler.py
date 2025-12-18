"""
行业资金流向 Handler

从 Tushare 获取行业资金流向数据（同花顺）。

业务逻辑：
1. 调用 Tushare moneyflow_ind_ths API
2. 每日盘后更新，单次调用返回当日所有行业的数据
"""
from typing import List, Dict, Any
from loguru import logger

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from utils.date.date_utils import DateUtils


class IndustryCapitalFlowHandler(BaseDataSourceHandler):
    """
    行业资金流向 Handler
    
    特点：
    - 单API，简单宏观数据
    - 每个交易日返回约90个行业的数据
    - 增量更新（incremental）
    """
    
    # 类属性（必须定义）
    data_source = "industry_capital_flow"
    renew_type = "incremental"  # 增量更新
    description = "获取行业资金流向数据（同花顺）"
    dependencies = []  # 不依赖其他数据源
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        # 默认日期范围：最近 1 年
        self.default_date_range = params.get('default_date_range', {"years": 1})
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        计算需要更新的日期范围（日度数据）
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return
        
        # 从 data_manager 查询数据库获取最新日期
        if self.data_manager:
            try:
                industry_capital_flow_model = self.data_manager.get_model('industry_capital_flow')
                if industry_capital_flow_model:
                    latest_record = industry_capital_flow_model.load_one(
                        condition="1=1",
                        order_by="date DESC"
                    )
                    if latest_record:
                        latest_date = latest_record.get('date', '')
                        if latest_date:
                            # 最新日期是 YYYYMMDD 格式，计算下一天作为开始日期
                            context["start_date"] = DateUtils.get_date_after_days(latest_date, 1)
                            logger.debug(f"从数据库查询到最新日期: {latest_date}，开始日期: {context['start_date']}")
            except Exception as e:
                logger.warning(f"查询数据库失败，使用默认日期范围: {e}")
        
        # 计算默认日期范围（如果没有从数据库获取到）
        if "start_date" not in context or "end_date" not in context:
            start_date, end_date = self._calculate_default_date_range()
            context["start_date"] = start_date
            context["end_date"] = end_date
            logger.debug(f"使用默认日期范围: {start_date} 至 {end_date}")
    
    def _calculate_default_date_range(self) -> tuple[str, str]:
        """
        根据配置计算默认日期范围（日期格式：YYYYMMDD）
        
        Returns:
            tuple: (start_date, end_date) 格式为 YYYYMMDD
        """
        current_date = DateUtils.get_current_date_str()
        
        if "years" in self.default_date_range:
            years = self.default_date_range["years"]
            start_date = DateUtils.get_date_before_days(current_date, years * 365)
        elif "days" in self.default_date_range:
            days = self.default_date_range["days"]
            start_date = DateUtils.get_date_before_days(current_date, days)
        else:
            start_date = DateUtils.get_date_before_days(current_date, 365)
        
        end_date = current_date
        
        return start_date, end_date
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取行业资金流向数据的 Tasks
        
        逻辑：
        1. 从 context 获取日期范围
        2. 创建一个 ApiJob 调用 moneyflow_ind_ths API
        """
        context = context or {}
        
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        
        if not start_date or not end_date:
            raise ValueError("IndustryCapitalFlowHandler 需要 start_date 和 end_date 参数")
        
        logger.debug(f"为行业资金流向数据生成任务: {start_date} 至 {end_date}")
        
        # 创建 ApiJob
        moneyflow_job = ApiJob(
            provider_name="tushare",
            method="get_moneyflow_ind_ths",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
            job_id="moneyflow_ind_ths_data",
            api_name="get_moneyflow_ind_ths"
        )
        
        # 创建一个 Task
        task = DataSourceTask(
            task_id="industry_capital_flow_data",
            api_jobs=[moneyflow_job],
            description=f"获取行业资金流向数据: {start_date} 至 {end_date}",
        )
        
        logger.info(f"✅ 生成了 1 个行业资金流向数据获取任务")
        
        return [task]
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare moneyflow_ind_ths API 的结果中处理数据
        """
        formatted = []
        
        # task_results 的结构：{task_id: {job_id: result}}
        task_result = task_results.get("industry_capital_flow_data", {})
        
        if not task_result:
            logger.warning("行业资金流向数据任务结果为空")
            return {"data": []}
        
        # 获取 API 的结果
        moneyflow_df = task_result.get("moneyflow_ind_ths_data")
        
        if moneyflow_df is None or moneyflow_df.empty:
            logger.warning("行业资金流向数据为空")
            return {"data": []}
        
        # 处理数据
        for _, row in moneyflow_df.iterrows():
            trade_date = str(row.get('trade_date', ''))
            if not trade_date:
                continue
            
            # 统一日期格式为 YYYYMMDD
            date_ymd = trade_date.replace('-', '') if '-' in trade_date else trade_date
            
            record = {
                'date': date_ymd,
                'industry': str(row.get('industry', '')),
                'industry_id': str(row.get('ts_code', '')),
                'company_number': int(row.get('company_num', 0)),
                'net_buy_amount': float(row.get('net_buy_amount', 0)),
                'net_sell_amount': float(row.get('net_sell_amount', 0)),
                'net_amount': float(row.get('net_amount', 0)),
                'index_change_percent': float(row.get('pct_change', 0)),
            }
            
            formatted.append(record)
        
        logger.info(f"✅ 行业资金流向数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }

