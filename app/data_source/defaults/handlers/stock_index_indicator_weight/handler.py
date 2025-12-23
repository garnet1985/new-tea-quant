"""
股指成分股权重 Handler

从 Tushare 获取指数成分股权重数据。

业务逻辑：
1. 调用 Tushare index_weight API
2. 为每个指数生成一个 Task
3. 指数成分股不常变化，至少1个月才更新
"""
from typing import List, Dict, Any
from loguru import logger

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from utils.date.date_utils import DateUtils


class StockIndexIndicatorWeightHandler(BaseDataSourceHandler):
    """
    股指成分股权重 Handler
    
    特点：
    - 为每个指数生成一个job
    - 单API，简单mapping
    - 指数成分股不常变化，至少1个月才更新
    """
    
    # 类属性（必须定义）
    data_source = "stock_index_indicator_weight"
    renew_type = "incremental"  # 增量更新
    description = "获取股指成分股权重数据"
    dependencies = []  # 不依赖其他数据源
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        # 默认指数列表
        self.index_list = params.get('index_list', [
            {'id': '000001.SH', 'name': '上证指数'},
            {'id': '000300.SH', 'name': '沪深300'},
            {'id': '000688.SH', 'name': '科创50'},
            {'id': '399001.SZ', 'name': '深证成指'},
            {'id': '399006.SZ', 'name': '创业板指'},
        ])
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        计算需要更新的日期范围（月度数据）
        """
        # 注意：不能用 context = context or {}，否则外部传入的空 dict 会被替换，
        # 导致在 fetch 阶段拿不到这里写入的 index_latest_dates / end_date
        if context is None:
            context = {}
        
        # 如果 context 中已有日期范围，直接使用
        if "start_date" in context and "end_date" in context:
            logger.debug(f"使用 context 中的日期范围: {context['start_date']} 至 {context['end_date']}")
            return
        
        # 从 data_manager 查询数据库获取最新日期（按指数分组）
        index_latest_dates = {}  # {index_id: latest_date}
        if self.data_manager:
            try:
                weight_model = self.data_manager.get_model('stock_index_indicator_weight')
                if weight_model:
                    # 获取所有指数的最新记录
                    all_latest_records = weight_model.load_latest_records(
                        date_field='date',
                        primary_keys=['id']  # 按指数ID分组
                    )
                    
                    for record in all_latest_records:
                        index_id = record.get('id')
                        latest_date = record.get('date')
                        if index_id and latest_date:
                            index_latest_dates[index_id] = latest_date
                    
                    logger.debug(f"查询到 {len(index_latest_dates)} 个指数的历史记录")
            except Exception as e:
                logger.warning(f"查询数据库失败: {e}")
        
        context["index_latest_dates"] = index_latest_dates
        
        # 获取最新交易日（用于计算结束日期）
        if self.data_manager:
            try:
                latest_trading_date = self.data_manager.get_latest_completed_trading_date()
                # 实际结束日期是前一个交易日
                context["end_date"] = DateUtils.get_date_before_days(latest_trading_date, 1)
            except Exception as e:
                logger.warning(f"获取最新交易日失败: {e}")
                context["end_date"] = DateUtils.get_current_date_str()
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取股指成分股权重数据的 Tasks
        
        逻辑：
        1. 为每个指数创建一个 Task
        2. 每个 Task 包含 1 个 ApiJob（index_weight）
        """
        context = context or {}
        
        end_date = context.get("end_date")
        index_latest_dates = context.get("index_latest_dates", {})
        
        if not end_date:
            raise ValueError("StockIndexIndicatorWeightHandler 需要 end_date 参数")
        
        tasks = []
        
        for index_info in self.index_list:
            index_id = index_info['id']
            index_name = index_info.get('name', index_id)
            
            # 计算开始日期
            latest_date = index_latest_dates.get(index_id)
            
            if latest_date:
                # 有历史记录，检查是否需要更新（至少1个月才更新）
                time_gap_days = DateUtils.get_duration_in_days(latest_date, end_date)
                if time_gap_days < 30:  # 至少30天才更新
                    continue
                
                start_date = DateUtils.get_date_after_days(latest_date, 1)
            else:
                # 无历史记录，使用默认起始日期
                from app.conf.conf import data_default_start_date
                start_date = data_default_start_date
            
            # 如果开始日期大于结束日期，跳过
            if start_date > end_date:
                continue
            
            # 创建 ApiJob
            weight_job = ApiJob(
                provider_name="tushare",
                method="get_index_weight",
                params={
                    "index_code": index_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                job_id=f"{index_id}_weight",
                api_name="get_index_weight"
            )
            
            # 创建 Task
            task = DataSourceTask(
                task_id=f"index_weight_{index_id}",
                api_jobs=[weight_job],
                description=f"获取 {index_name} ({index_id}) 的成分股权重数据",
            )
            tasks.append(task)
        
        logger.info(f"✅ 生成了 {len(tasks)} 个指数成分股权重数据获取任务")
        
        return tasks
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据
        
        从 Tushare index_weight API 的结果中处理数据
        """
        formatted = []
        
        # task_results 的结构：{task_id: {job_id: result}}
        for task_id, task_result in task_results.items():
            if not task_id.startswith("index_weight_"):
                continue
            
            index_id = task_id.replace("index_weight_", "")
            
            # 获取 API 的结果
            weight_df = task_result.get(f"{index_id}_weight")
            
            if weight_df is None or weight_df.empty:
                continue
            
            # 处理数据
            for _, row in weight_df.iterrows():
                trade_date = str(row.get('trade_date', ''))
                if not trade_date:
                    continue
                
                # 统一日期格式为 YYYYMMDD
                date_ymd = trade_date.replace('-', '') if '-' in trade_date else trade_date
                
                record = {
                    'id': index_id,
                    'date': date_ymd,
                    'stock_id': str(row.get('con_code', '')),
                    'weight': float(row.get('weight', 0)),
                }
                
                formatted.append(record)
        
        logger.info(f"✅ 股指成分股权重数据处理完成，共 {len(formatted)} 条记录")
        
        return {
            "data": formatted
        }

    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """
        标准化后处理：保存股指成分股权重数据到数据库
        """
        context = context or {}

        dry_run = context.get("dry_run", False)
        if dry_run:
            logger.info("🧪 干运行模式：跳过股指成分股权重数据保存")
            return

        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存股指成分股权重数据")
            return

        data_list = normalized_data.get("data") if isinstance(normalized_data, dict) else None
        if not data_list:
            logger.debug("股指成分股权重数据为空，无需保存")
            return

        try:
            from utils.db.db_base_model import DBService
            data_list = DBService.clean_nan_in_list(data_list, default=0.0)

            model = self.data_manager.get_model("stock_index_indicator_weight")
            if not model:
                logger.error("未找到 stock_index_indicator_weight Model，无法保存数据")
                return

            # 使用表 schema 的主键 (id, date, stock_id) 去重
            count = model.replace(data_list, unique_keys=["id", "date", "stock_id"])
            logger.info(f"✅ 股指成分股权重数据保存完成，共 {count} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存股指成分股权重数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

