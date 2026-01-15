"""
企业财务数据 Handler

从 Tushare 获取企业财务指标数据（季度）
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger

from core.config.loaders.system_conf import data_default_start_date
from core.modules.data_source.data_source_handler import BaseDataSourceHandler
from core.modules.data_source.api_job import DataSourceTask, ApiJob
from core.utils.date.date_utils import DateUtils
from core.infra.db.db_base_model import DBService


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
    description = "获取企业财务指标数据（季度）"
    dependencies = []  # 依赖数据源
    
    # 可选类属性
    requires_date_range = True  # 需要日期范围参数
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)

        # 滚动窗口：默认每次至少覆盖最近 N 个季度
        # 说明：
        # - 对“已跟上节奏”的股票，每次会刷新最近 ROLLING_QUARTERS 个季度
        # - 对于长期未更新的股票，不再做最大季度数限制，而是从上次更新的季度起点一路补到当前有效季度
        #   （数据一致性优先于单次任务性能）
        self.ROLLING_QUARTERS = 3
        # 轮转批次数：当数据表不为空时，将当前 stock_list 按轮转游标切成批次，
        # 每次 run 只处理约 1/RENEW_ROLLING_BATCH 的股票，长期来看覆盖整个股票池。
        # 示例：RENEW_ROLLING_BATCH = 10 且 stock_list 长度为 5000，
        #      每次大约处理 500 只股票。
        self.RENEW_ROLLING_BATCH = 8

    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段
        
        查询数据库获取最新季度，计算需要更新的日期范围
        获取股票列表
        """
        context = context or {}
        stock_list = context.get("stock_list", [])
        
        # 获取最新完成交易日（优先从 context 读取，由 renew_data() 统一获取并注入）
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            if self.data_manager:
                # 兜底：如果 context 中没有，才自己获取（不应该发生，但保留兜底逻辑）
                logger.warning("CorporateFinanceHandler.before_fetch: context 中未找到 latest_completed_trading_date，回退获取")
                latest_completed_trading_date = self.data_manager.service.calendar.get_latest_completed_trading_date()
            else:
                logger.warning("无法获取最新完成交易日，跳过企业财务数据更新")
                return context
        
        # 构建需要更新的股票列表
        target_list = self._build_renewable_stock_list(latest_completed_trading_date, stock_list)

        if len(target_list) == 0:
            logger.info("没有需要更新的股票")
            return context
        
        context["target_list"] = target_list
        context["latest_completed_trading_date"] = latest_completed_trading_date
        
        logger.info(f"✅ 筛选出 {len(target_list)} 只股票需要更新企业财务数据")
        return context

    def _build_renewable_stock_list(self, latest_completed_trading_date: str, stock_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        构建需要更新的股票列表
        
        Args:
            latest_completed_trading_date: 最新完成交易日（YYYYMMDD格式）
        
        Returns:
            List[Dict]: 需要更新的股票列表，每个元素包含：
                - stock_id: 股票代码
                - start_date: 起始日期（YYYYMMDD格式）
                - end_date: 结束日期（YYYYMMDD格式）
        """
        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法构建股票列表")
            return []
        
        # 计算当前季度，作为本次任务的“有效上界”季度
        # 简化规则：不再等待额外的 buffer，只要 latest_completed_trading_date
        # 落在某个季度内，就认为该季度可以参与 renew。
        max_effective_quarter = DateUtils.get_current_quarter(latest_completed_trading_date)
        # 以 max_effective_quarter 为窗口上界，默认滚动覆盖最近 ROLLING_QUARTERS 个季度
        # 从 DB 中获取所有股票最新的财报季度信息：{stock_id: last_updated_quarter}
        raw_map = self.data_manager.service.stock.corporate_finance.get_stocks_latest_update_quarter()
        
        # 如果 DB 里完全没有企业财务数据，这是第一次跑：
        # 为了建立基准数据，对所有股票从默认起点开始全量拉取到当前有效季度。
        is_first_run = not raw_map
        
        target_list = []
        # end_date 直接使用 latest_completed_trading_date
        # （我们以自然日为上界，不再强制截到季度末尾）
        end_date = latest_completed_trading_date
        
        # 系统的历史起点季度（由 data_default_start_date 决定）
        base_quarter = DateUtils.date_to_quarter(data_default_start_date)
        
        # 工具函数：将季度转为线性索引，便于计算季度差距
        def quarter_to_index(q_str: str) -> int:
            year = int(q_str[:4])
            quarter = int(q_str[5])
            return year * 4 + quarter
        
        max_index = quarter_to_index(max_effective_quarter)

        # ========== 轮转批次选择 ==========
        # - 首次跑（is_first_run=True）：对传入的 stock_list 全量处理，建立基准库
        # - 非首次：使用 meta_info 表中的游标进行轮转，避免总是命中前缀
        all_stocks = list(stock_list or [])
        if not all_stocks:
            return []

        effective_stock_list = all_stocks
        batch_size = len(all_stocks)
        batch_offset = 0

        if not is_first_run and self.RENEW_ROLLING_BATCH and len(all_stocks) > 0:

            batch_size = max(1, len(all_stocks) // self.RENEW_ROLLING_BATCH)

            try:
                # 使用 service 访问缓存
                cache_key = 'corporate_finance_batch_offset'
                cache_row = self.data_manager.db_cache.get(cache_key)
                if cache_row and cache_row.get('value') is not None:
                    try:
                        batch_offset = int(cache_row['value'])
                    except (TypeError, ValueError):
                        batch_offset = 0
                else:
                    batch_offset = 0
            except Exception as e:
                logger.warning(f"读取 system_cache 批次游标失败，将从头开始轮转: {e}")
                batch_offset = 0

            # 根据 offset 做环形切片
            L = len(all_stocks)
            indices = [(batch_offset + i) % L for i in range(batch_size)]
            effective_stock_list = [all_stocks[i] for i in indices]

            # 预先计算新的 offset，用于本次 run 结束后持久化
            new_offset = (batch_offset + batch_size) % L
        else:
            new_offset = 0  # 首次跑或不开启轮转时，不使用 offset

        # 针对本次选中的股票逐一决定起始日期
        for stock in effective_stock_list:
            stock_id = stock.get("id") or stock.get("ts_code")
            if not stock_id:
                continue
            
            # 第一次跑：对所有股票从系统默认起点全量拉取
            if is_first_run:
                start_date = data_default_start_date
            else:
                last_q = raw_map.get(stock_id)
                
                if not last_q:
                    # DB 中没有这只股票：视为新股，从默认起点开始全量拉取
                    start_date = data_default_start_date
                else:
                    # 下一个应更新的季度
                    next_q = DateUtils.get_next_quarter(last_q)
                    next_index = quarter_to_index(next_q)
                    
                    # 计算“滚动窗口”的最老季度：max_q 往前 ROLLING_QUARTERS-1 个季度
                    window_oldest_index = max_index - (self.ROLLING_QUARTERS - 1)
                    window_oldest_quarter = base_quarter
                    if quarter_to_index(base_quarter) < window_oldest_index:
                        tmp_q = base_quarter
                        while quarter_to_index(tmp_q) < window_oldest_index:
                            tmp_q = DateUtils.get_next_quarter(tmp_q)
                        window_oldest_quarter = tmp_q
                    
                    # 情况 1：如果 next_q 已经落在或早于窗口起点，说明“追平进度”后，
                    # 只需要滚动刷新最近 ROLLING_QUARTERS 个季度即可。
                    if next_index <= window_oldest_index:
                        start_quarter = window_oldest_quarter
                    else:
                        # 情况 2：这只股票落后超过 ROLLING_QUARTERS 个季度，
                        # 需要从 last_q 对应季度的起点开始回补，一路补到当前有效季度。
                        start_quarter = last_q
                    
                    # 将起始季度转换为日期
                    start_date = DateUtils.get_start_date_of_quarter(start_quarter)
            
            target_list.append({
                "stock_id": stock_id,
                "start_date": start_date,
                "end_date": end_date,
            })

        # 非首次跑时，将新的 batch_offset 写回 system_cache，作为下次轮转的起点
        if not is_first_run and self.RENEW_ROLLING_BATCH and target_list:
            try:
                # 使用 service 保存缓存
                cache_key = 'corporate_finance_batch_offset'
                self.data_manager.db_cache.set(
                    key=cache_key,
                    value=str(new_offset)
                )
            except Exception as e:
                logger.warning(f"写入 system_cache 批次游标失败，不影响本次任务: {e}")
        
        return target_list

    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取企业财务数据的 Tasks
        
        逻辑：
        1. 从 context 获取需要更新的股票列表（包含 start_date 和 end_date）
        2. 为每个股票创建一个 Task（包含一个 ApiJob）
        3. 每个 ApiJob 调用 Tushare fina_indicator API
        """
        context = context or {}
        target_list = context.get("target_list", [])
        
        if not target_list:
            logger.info("没有需要更新的股票")
            return []

        tasks = []
        for stock in target_list:
            stock_id = stock.get('stock_id')
            start_date = stock.get('start_date')
            end_date = stock.get('end_date')
            
            if not stock_id or not start_date or not end_date:
                logger.warning(f"股票 {stock_id} 缺少必要参数（start_date 或 end_date）")
                continue

            # 创建 ApiJob
            api_job = ApiJob(
                provider_name="tushare",
                method="get_finance_data",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                job_id=f"{stock_id}_finance",
                api_name="get_finance_data"
            )
            
            # 创建 Task
            task = DataSourceTask(
                task_id=f"corporate_finance_{stock_id}",
                api_jobs=[api_job],
                description=f"获取 {stock_id} 的企业财务数据（{start_date} 至 {end_date}）"
            )

            tasks.append(task)
        
        logger.info(f"✅ 生成了 {len(tasks)} 个企业财务数据获取任务")
        return tasks

    # ========== 执行阶段钩子 ==========

    async def after_single_task_execute(
        self,
        task_id: str,
        task_result: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """
        单个 Task 执行完成后的钩子：就地保存该股票的企业财务数据。

        和复权因子类似，避免在所有股票都跑完之后一次性落库，
        改为“一个股票一保存”，减少大批量写入导致的风险。
        """
        context = context or {}

        # 干运行模式：只跑流程，不写库
        if context.get("dry_run"):
            logger.info(f"🧪 干运行模式：跳过 {task_id} 的企业财务数据保存")
            return

        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存企业财务数据")
            return

        try:
            # 复用 normalize 逻辑，对单个 task 结果做标准化
            single_raw = {task_id: task_result}
            normalized = await self.normalize(single_raw)

            data_list = self._validate_data_for_save(normalized)
            if not data_list:
                logger.info(f"ℹ️ {task_id} 没有有效企业财务数据，跳过保存")
                return

            # 使用 service 保存数据
            saved_count = self.data_manager.stock.corporate_finance.save_batch(data_list)
            logger.info(f"✅ [单股票保存] {task_id}: 保存 {saved_count} 条企业财务记录")
        except Exception as e:
            logger.error(f"❌ 保存 {task_id} 企业财务数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    
    async def after_normalize(self, normalized_data: Dict[str, Any]):
        """
        标准化后处理（全局）：这里只做日志，不再统一写库。

        企业财务数据的落库已经在 after_single_task_execute 中
        按股票粒度完成，避免重复保存。
        """
        data_list = normalized_data.get("data") or []
        logger.info(f"✅ 企业财务数据标准化完成（按股票已分别保存），总记录数: {len(data_list)}")
    
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
            
            # 使用 DBService 清理所有记录中的 NaN 值
            records = DBService.clean_nan_in_list(records, default=None)
            
            # 字段映射和数据处理
            for item in records:
                # 将 end_date 转换为 quarter
                end_date = str(item.get('end_date', ''))
                # 确保 end_date 是 YYYYMMDD 格式
                if '-' in end_date:
                    end_date = end_date.replace('-', '')
                
                quarter = DateUtils.date_to_quarter(end_date)
                
                if not quarter:
                    logger.debug(f"无法将日期 {end_date} 转换为季度，跳过该记录")
                    continue
                
                # 辅助函数：安全地将值转换为 float，处理 NaN
                def safe_float(value, default=0.0):
                    """安全转换为 float，处理 NaN 和 None"""
                    # 使用 DBService 的通用方法清理 NaN
                    cleaned = DBService.clean_nan_value(value, default=None)
                    if cleaned is None:
                        return default
                    try:
                        result = float(cleaned)
                        # 再次检查转换后的值是否是 NaN（双重保险）
                        if cleaned is not None and isinstance(result, float):
                            import math
                            if math.isnan(result):
                                return default
                        return result
                    except (TypeError, ValueError):
                        return default
                
                # 字段映射（根据 legacy config）
                mapped = {
                    "id": item.get('ts_code', ''),
                    "quarter": quarter,
                    # 盈利能力指标
                    "eps": safe_float(item.get('eps')),
                    "dt_eps": safe_float(item.get('dt_eps')),
                    "roe": safe_float(item.get('roe')),
                    "roe_dt": safe_float(item.get('roe_dt')),
                    "roa": safe_float(item.get('roa')),
                    "netprofit_margin": safe_float(item.get('netprofit_margin')),
                    "gross_profit_margin": safe_float(item.get('grossprofit_margin')),  # API字段名差异
                    "op_income": safe_float(item.get('op_income')),
                    "roic": safe_float(item.get('roic')),
                    "ebit": safe_float(item.get('ebit')),
                    "ebitda": safe_float(item.get('ebitda')),
                    "dtprofit_to_profit": safe_float(item.get('dtprofit_to_profit')),
                    "profit_dedt": safe_float(item.get('profit_dedt')),
                    # 成长能力指标
                    "or_yoy": safe_float(item.get('or_yoy')),
                    "netprofit_yoy": safe_float(item.get('netprofit_yoy')),
                    "basic_eps_yoy": safe_float(item.get('basic_eps_yoy')),
                    "dt_eps_yoy": safe_float(item.get('dt_eps_yoy')),
                    "tr_yoy": safe_float(item.get('tr_yoy')),
                    # 偿债能力指标
                    "netdebt": safe_float(item.get('netdebt')),
                    "debt_to_eqt": safe_float(item.get('debt_to_eqt')),
                    "debt_to_assets": safe_float(item.get('debt_to_assets')),
                    "interestdebt": safe_float(item.get('interestdebt')),
                    "assets_to_eqt": safe_float(item.get('assets_to_eqt')),
                    "quick_ratio": safe_float(item.get('quick_ratio')),
                    "current_ratio": safe_float(item.get('current_ratio')),
                    # 运营能力指标
                    "ar_turn": safe_float(item.get('ar_turn')),
                    # 资产状况指标
                    "bps": safe_float(item.get('bps')),
                    # 现金流指标
                    "ocfps": safe_float(item.get('ocfps')),
                    "fcff": safe_float(item.get('fcff')),
                    "fcfe": safe_float(item.get('fcfe')),
                }
                
                # 只保留有效的记录（必须有 id 和 quarter）
                if mapped.get('id') and mapped.get('quarter'):
                    formatted.append(mapped)
        
        return {
            "data": formatted
        }
