"""
企业财务数据 Handler

从 Tushare 获取企业财务指标数据（季度）
"""
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from utils.date.date_utils import DateUtils


class CorporateFinanceHandler(BaseDataSourceHandler):
    """
    企业财务数据 Handler
    
    从 Tushare 获取企业财务指标数据（季度）。
    
    特点：
    - 季度数据（YYYYQ[1-4] 格式）
    - 增量更新（incremental）
    - 需要按股票逐个获取（每个股票一个 Task）
    - 需要计算日期范围（基于数据库最新记录）
    """
    
    # 类属性（必须定义）
    data_source = "corporate_finance"
    renew_type = "incremental"  # 增量更新
    description = "获取企业财务指标数据（季度）"
    dependencies = ["stock_list"]  # 依赖股票列表
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None):
        super().__init__(schema, params or {})
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        查询数据库获取最新季度，计算需要更新的日期范围
        获取股票列表
        """
        context = context or {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
        else:
            # 从 data_manager 查询数据库获取最新季度
            if self.data_manager:
                try:
                    # TODO: 查询数据库获取最新季度
                    logger.debug("从数据库查询最新季度（待实现）")
                except Exception as e:
                    logger.warning(f"查询数据库失败，使用默认日期范围: {e}")
            
            # 如果没有数据库或查询失败，使用默认范围（最近 2 年）
            if "start_date" not in context or "end_date" not in context:
                # 默认：最近 2 年的数据
                current_year = datetime.now().year
                current_month = datetime.now().month
                # 计算当前季度
                if current_month <= 3:
                    current_quarter = 1
                elif current_month <= 6:
                    current_quarter = 2
                elif current_month <= 9:
                    current_quarter = 3
                else:
                    current_quarter = 4
                
                context["start_date"] = f"{current_year - 2}Q1"
                context["end_date"] = f"{current_year}Q{current_quarter}"
                logger.debug(f"使用默认日期范围: {context['start_date']} 至 {context['end_date']}")
        
        # 获取股票列表（从依赖或 context）
        if "stock_list" not in context:
            # TODO: 从依赖的 stock_list data source 获取
            # 或者从 data_manager 查询数据库
            logger.warning("股票列表未提供，将无法获取财务数据")
            context["stock_list"] = []
    
    async def fetch(self, context: Dict[str, Any] = None) -> List:
        """
        生成获取企业财务数据的 Tasks
        
        逻辑：
        1. 从 context 获取股票列表和日期范围
        2. 为每个股票创建一个 Task（包含一个 ApiJob）
        3. 每个 ApiJob 调用 Tushare fina_indicator API
        """
        context = context or {}
        
        stock_list = context.get("stock_list", [])
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        
        if not stock_list:
            logger.warning("股票列表为空，无法获取财务数据")
            return []
        
        if not start_date or not end_date:
            raise ValueError("Corporate Finance Handler 需要 start_date 和 end_date 参数")
        
        # 如果日期是季度格式（YYYYQ[1-4]），转换为日期格式（YYYYMMDD）
        # Tushare fina_indicator API 需要日期格式
        if len(start_date) == 6 and start_date[4] == 'Q':
            start_date = DateUtils.quarter_to_date(start_date, is_start=True)
        if len(end_date) == 6 and end_date[4] == 'Q':
            end_date = DateUtils.quarter_to_date(end_date, is_start=False)
        
        logger.debug(f"为 {len(stock_list)} 只股票生成财务数据获取任务: {start_date} 至 {end_date}")
        
        # 为每个股票创建一个 Task
        tasks = []
        for stock in stock_list:
            stock_id = stock.get('id') if isinstance(stock, dict) else stock
            if not stock_id:
                continue
            
            # 创建 ApiJob
            api_job = ApiJob(
                provider_name="tushare",
                method="get_finance_data",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
            
            # 创建 Task
            task = DataSourceTask(
                task_id=f"corporate_finance_{stock_id}",
                api_jobs=[api_job],
            )
            
            tasks.append(task)
        
        logger.info(f"✅ 生成了 {len(tasks)} 个财务数据获取任务")
        
        return tasks
    
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare 返回的 DataFrame 中提取财务数据，进行字段映射
        每个 Task 对应一个股票的数据
        """
        formatted = []
        
        # raw_data 的结构：{task_id: {job_id: result}}
        for task_id, task_results in raw_data.items():
            if not task_results:
                continue
            
            # 获取该股票的数据（每个 task 只有一个 job）
            job_id = list(task_results.keys())[0]
            df = task_results[job_id]
            
            if df is None or df.empty:
                continue
            
            # 转换为字典列表
            records = df.to_dict('records')
            
            # 字段映射和数据处理
            for item in records:
                # 将 end_date 转换为 quarter
                end_date = str(item.get('end_date', ''))
                quarter = DateUtils.date_to_quarter(end_date)
                
                if not quarter:
                    continue
                
                # 字段映射（根据 legacy config）
                mapped = {
                    "id": item.get('ts_code', ''),
                    "quarter": quarter,
                    # 盈利能力指标
                    "eps": float(item.get('eps', 0)) if item.get('eps') is not None else 0.0,
                    "dt_eps": float(item.get('dt_eps', 0)) if item.get('dt_eps') is not None else 0.0,
                    "roe": float(item.get('roe', 0)) if item.get('roe') is not None else 0.0,
                    "roe_dt": float(item.get('roe_dt', 0)) if item.get('roe_dt') is not None else 0.0,
                    "roa": float(item.get('roa', 0)) if item.get('roa') is not None else 0.0,
                    "netprofit_margin": float(item.get('netprofit_margin', 0)) if item.get('netprofit_margin') is not None else 0.0,
                    "gross_profit_margin": float(item.get('grossprofit_margin', 0)) if item.get('grossprofit_margin') is not None else 0.0,  # API字段名差异
                    "op_income": float(item.get('op_income', 0)) if item.get('op_income') is not None else 0.0,
                    "roic": float(item.get('roic', 0)) if item.get('roic') is not None else 0.0,
                    "ebit": float(item.get('ebit', 0)) if item.get('ebit') is not None else 0.0,
                    "ebitda": float(item.get('ebitda', 0)) if item.get('ebitda') is not None else 0.0,
                    "dtprofit_to_profit": float(item.get('dtprofit_to_profit', 0)) if item.get('dtprofit_to_profit') is not None else 0.0,
                    "profit_dedt": float(item.get('profit_dedt', 0)) if item.get('profit_dedt') is not None else 0.0,
                    # 成长能力指标
                    "or_yoy": float(item.get('or_yoy', 0)) if item.get('or_yoy') is not None else 0.0,
                    "netprofit_yoy": float(item.get('netprofit_yoy', 0)) if item.get('netprofit_yoy') is not None else 0.0,
                    "basic_eps_yoy": float(item.get('basic_eps_yoy', 0)) if item.get('basic_eps_yoy') is not None else 0.0,
                    "dt_eps_yoy": float(item.get('dt_eps_yoy', 0)) if item.get('dt_eps_yoy') is not None else 0.0,
                    "tr_yoy": float(item.get('tr_yoy', 0)) if item.get('tr_yoy') is not None else 0.0,
                    # 偿债能力指标
                    "netdebt": float(item.get('netdebt', 0)) if item.get('netdebt') is not None else 0.0,
                    "debt_to_eqt": float(item.get('debt_to_eqt', 0)) if item.get('debt_to_eqt') is not None else 0.0,
                    "debt_to_assets": float(item.get('debt_to_assets', 0)) if item.get('debt_to_assets') is not None else 0.0,
                    "interestdebt": float(item.get('interestdebt', 0)) if item.get('interestdebt') is not None else 0.0,
                    "assets_to_eqt": float(item.get('assets_to_eqt', 0)) if item.get('assets_to_eqt') is not None else 0.0,
                    "quick_ratio": float(item.get('quick_ratio', 0)) if item.get('quick_ratio') is not None else 0.0,
                    "current_ratio": float(item.get('current_ratio', 0)) if item.get('current_ratio') is not None else 0.0,
                    # 运营能力指标
                    "ar_turn": float(item.get('ar_turn', 0)) if item.get('ar_turn') is not None else 0.0,
                    # 资产状况指标
                    "bps": float(item.get('bps', 0)) if item.get('bps') is not None else 0.0,
                    # 现金流指标
                    "ocfps": float(item.get('ocfps', 0)) if item.get('ocfps') is not None else 0.0,
                    "fcff": float(item.get('fcff', 0)) if item.get('fcff') is not None else 0.0,
                    "fcfe": float(item.get('fcfe', 0)) if item.get('fcfe') is not None else 0.0,
                }
                
                # 只保留有效的记录（必须有 id 和 quarter）
                if mapped.get('id') and mapped.get('quarter'):
                    formatted.append(mapped)
        
        logger.info(f"✅ 企业财务数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }
