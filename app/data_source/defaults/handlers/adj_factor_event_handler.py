"""
复权因子事件 Handler（新算法 - 批量扫描版）

根据优化方案，实现高效的批量扫描和更新流程：
0. CSV导入（如果表为空）
1. 批量查询超过N天未更新的股票
2. 多线程调用 Tushare adj_factor 预筛选（找出有因子变化的股票）
3. 为有变化的股票生成 tasks（Tushare adj_factor + daily_kline + EastMoney QFQ）
4. 保存数据
5. 处理新股票的第一天
6. 季度CSV导出
"""
from typing import List, Dict, Any
from loguru import logger
import os

from app.data_source.data_source_handler import BaseDataSourceHandler
from app.data_source.api_job import DataSourceTask, ApiJob
from app.data_source.defaults.handlers.adj_factor_event_handler_helper import AdjFactorEventHandlerHelper
from utils.date.date_utils import DateUtils


class AdjFactorEventHandler(BaseDataSourceHandler):
    """
    复权因子事件 Handler（新算法 - 批量扫描版）
    
    特点：
    - CSV缓存：空表时从CSV快速恢复
    - 批量筛选：一次SQL查询找出需要更新的股票
    - 预筛选优化：只对有因子变化的股票调用东方财富API
    - 多线程支持：预筛选和精确计算都支持多线程
    - 季度CSV导出：定期备份数据
    """
    
    # 类属性（必须定义）
    data_source = "adj_factor_event"
    renew_type = "incremental"  # 增量更新
    description = "获取复权因子事件数据（只存储除权日）"
    dependencies = ["stock_list", "kline"]  # 依赖股票列表和K线数据
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        # 从 params 读取配置
        self.update_threshold_days = params.get('update_threshold_days', 15)  # 默认15天
        self.max_workers = params.get('max_workers', 10)  # 最大线程数
        # 东方财富API限流：60次/分钟（需要手动控制）
        self.eastmoney_rate_limit = 60  # 每分钟60次
        self.eastmoney_min_interval = 60.0 / 60.0  # 每次请求间隔（秒）
        self._last_eastmoney_request_time = 0.0
    
    
    async def before_fetch(self, context: Dict[str, Any] = None):
        """
        数据准备阶段（步骤0-2）
        
        步骤0：如果表为空，尝试从CSV导入
        步骤1：批量查询超过N天未更新的股票
        步骤2：多线程调用 Tushare adj_factor 预筛选（找出有因子变化的股票）
        """
        context = context or {}
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化")
            return context
        
        adj_factor_event_model = self.data_manager.get_model('adj_factor_event')
        kline_model = self.data_manager.get_model('stock_kline')
        
        # ========== 步骤0：根据 DB / CSV 状态做初始化决策 ==========
        table_was_empty = AdjFactorEventHandlerHelper.is_table_empty(adj_factor_event_model)
        csv_usable = AdjFactorEventHandlerHelper.is_csv_usable(adj_factor_event_model)

        if table_was_empty:
            # Case 1 / Case 2：表为空
            if csv_usable:
                # Case 2：优先尝试从 CSV 暖启动
                logger.info("📋 步骤 0/6: 复权因子事件表为空，检测到可用 CSV，尝试导入...")
                imported_count = adj_factor_event_model.import_from_csv()
                if imported_count > 0:
                    logger.info(f"✅ 从CSV导入 {imported_count} 条记录")
                    table_was_empty = False
                else:
                    logger.info("ℹ️  CSV 导入失败或无数据，将按冷启动流程继续")
            else:
                logger.info("📋 步骤 0/6: 复权因子事件表为空，且无可用 CSV，将按冷启动流程继续")
        
        # ========== 步骤1：确定需要更新的股票集合 ==========
        context_stock_list = context.get("stock_list")
        
        if table_was_empty:
            # Case 1 / Case 2：表为空（可能是冷启动，也可能是 CSV 恢复失败）
            # 首次构建：如果有传入的 stock_list，则只针对这些股票；否则全量活跃股票
            if context_stock_list:
                stocks_need_update = [s['id'] if isinstance(s, dict) else s for s in context_stock_list]
                logger.info(f"📋 步骤 1/6: 空表首次构建，使用传入的 {len(stocks_need_update)} 只股票进行全量计算")
            else:
                logger.info("📋 步骤 1/6: 空表首次构建，使用全部活跃股票进行全量计算...")
                stock_service = self.data_manager.get_data_service('stock_related.stock')
                if stock_service:
                    all_stocks = stock_service.load_stock_list(filtered=True)
                    stocks_need_update = [s['id'] for s in all_stocks]
                else:
                    stocks_need_update = []
        elif context_stock_list:
            # Case 3 + 有传入 stock_list：
            # 1. 没有任何事件记录的股票 → 视为“首建对象”
            # 2. 其余股票后续走正常的“超过 N 天未更新”筛选逻辑
            stocks_need_update = []
            for s in context_stock_list:
                stock_id = s['id'] if isinstance(s, dict) else s
                stock_events = adj_factor_event_model.load("id = %s", (stock_id,), limit=1)
                if not stock_events:
                    # 该股票没有数据，需要首次构建
                    stocks_need_update.append(stock_id)
            
            if stocks_need_update:
                logger.info(f"📋 步骤 1/6: 检测到 {len(stocks_need_update)} 只股票没有数据，进行首次构建")
            else:
                # 所有传入股票都有数据，走正常增量模式：只看“超过 N 天未更新”的
                logger.info(f"📋 步骤 1/6: 查询超过 {self.update_threshold_days} 天未更新的股票...")
                stocks_need_update = adj_factor_event_model.load_stocks_need_update(self.update_threshold_days)
        else:
            # Case 3 + 无特定 stock_list：根据覆盖率决定策略
            stock_service = self.data_manager.get_data_service('stock_related.stock')
            if stock_service:
                all_stocks = stock_service.load_stock_list(filtered=True)
                all_ids = [s['id'] for s in all_stocks]
            else:
                all_ids = []

            existing_ids = AdjFactorEventHandlerHelper.get_stocks_with_existing_factors(adj_factor_event_model)
            coverage = AdjFactorEventHandlerHelper.compute_coverage_ratio(existing_ids, all_ids)

            logger.info(
                f"📊 当前 adj_factor_event 覆盖率: "
                f"{coverage * 100:.2f}% "
                f"（已有 {len(existing_ids)} 只股票有事件记录，总股票数 {len(all_ids)}）"
            )

            # 覆盖率阈值可调：低覆盖率 → 大部分股票需要首建；高覆盖率 → 只做增量扫描
            low_coverage_threshold = 0.7

            if coverage < low_coverage_threshold and all_ids:
                # 大部分股票还没有任何复权事件记录：
                # 1. 对“完全没有记录”的股票视为首建对象
                # 2. 对已经有记录的少数股票，后续通过 load_stocks_need_update 做增量扫描
                existing_set = set(existing_ids)
                missing_ids = [sid for sid in all_ids if sid not in existing_set]

                logger.info(
                    f"📋 步骤 1/6: 覆盖率较低（{coverage * 100:.2f}%），"
                    f"检测到 {len(missing_ids)} 只股票从未构建复权事件，将进行首次构建"
                )

                # 先把“首建对象”加入待更新列表
                stocks_need_update = list(missing_ids)

                # 再追加“超过 N 天未更新”的已有股票（去重）
                incremental_ids = adj_factor_event_model.load_stocks_need_update(self.update_threshold_days)
                stocks_need_update_set = set(stocks_need_update)
                for sid in incremental_ids:
                    if sid not in stocks_need_update_set:
                        stocks_need_update.append(sid)
                        stocks_need_update_set.add(sid)
            else:
                # 覆盖率已经较高，走正常增量模式：只处理超过 N 天未更新的股票
                logger.info(
                    f"📋 步骤 1/6: 覆盖率较高（{coverage * 100:.2f}%），"
                    f"仅查询超过 {self.update_threshold_days} 天未更新的股票"
                )
                stocks_need_update = adj_factor_event_model.load_stocks_need_update(self.update_threshold_days)
        
        if not stocks_need_update:
            logger.info("ℹ️  没有股票需要更新")
            context["stocks_with_changes"] = []
            return context
        
        logger.info(f"✅ 查询到 {len(stocks_need_update)} 只股票需要更新")
        
        # 获取最新交易日
        latest_trading_date = self.data_manager.get_latest_trading_date()
        if not latest_trading_date:
            latest_trading_date = DateUtils.get_current_date_str()
        
        # 批量获取每只股票的最新 event_date（优化：一次查询而不是 N 次）
        latest_factors_map = adj_factor_event_model.load_latest_factors_batch(stocks_need_update)
        
        # 获取每只股票的最新 event_date 和第一根K线日期
        stock_info_map = {}
        for stock_id in stocks_need_update:
            latest_event = latest_factors_map.get(stock_id)
            stock_info_map[stock_id] = {
                'latest_event_date': latest_event['event_date'] if latest_event else None,
                'first_kline_date': None,  # 稍后批量查询
            }
        
        # 批量查询第一根K线日期（仅针对需要更新的股票）
        first_kline_records = kline_model.load_first_kline_records(stock_ids=stocks_need_update)
        first_kline_map = {r['id']: r['date'] for r in first_kline_records}
        for stock_id in stock_info_map:
            stock_info_map[stock_id]['first_kline_date'] = first_kline_map.get(stock_id)
        
        context["stock_info_map"] = stock_info_map
        context["latest_trading_date"] = latest_trading_date
        
        # ========== 步骤2：多线程预筛选（找出有因子变化的股票）==========
        logger.info(f"📋 步骤 2/6: 多线程预筛选（最多 {self.max_workers} 个线程）...")
        stocks_with_changes = AdjFactorEventHandlerHelper.prefilter_stocks_with_changes(
            stocks_need_update, 
            stock_info_map, 
            latest_trading_date,
            self.max_workers
        )
        
        logger.info(f"✅ 预筛选完成，{len(stocks_with_changes)} 只股票有复权事件")
        context["stocks_with_changes"] = stocks_with_changes
        
        return context
    
    async def fetch(self, context: Dict[str, Any] = None) -> List[DataSourceTask]:
        """
        生成获取复权因子事件的 Tasks（步骤3）
        
        优化方案：以股票为单位生成 task，每个 task 包含 3 个全量 API 调用：
        - Tushare adj_factor API（全量复权因子）
        - Tushare daily_kline API（全量原始收盘价）
        - EastMoney API（全量前复权价格）
        
        这样可以将 API 调用次数从 事件数×3 降低到 股票数×3
        """
        context = context or {}
        stocks_with_changes = context.get("stocks_with_changes", [])
        latest_trading_date = context.get("latest_trading_date")
        
        if not stocks_with_changes:
            logger.info("没有股票有复权事件，无需生成 tasks")
            return []
        
        if not latest_trading_date:
            latest_trading_date = self.data_manager.get_latest_trading_date() if self.data_manager else DateUtils.get_current_date_str()
        
        tasks = []
        stock_info_map = context.get("stock_info_map", {})
        end_date_ymd = DateUtils.yyyy_mm_dd_to_yyyymmdd(latest_trading_date) if '-' in latest_trading_date else latest_trading_date
        
        for stock_info in stocks_with_changes:
            stock_id = stock_info['stock_id']
            info = stock_info_map.get(stock_id, {})
            first_kline_date = info.get('first_kline_date')
            
            # 全量重算起点：优先使用第一根K线日期，否则使用默认起点
            if first_kline_date:
                start_date_full = DateUtils.yyyy_mm_dd_to_yyyymmdd(first_kline_date) if '-' in first_kline_date else first_kline_date
            else:
                start_date_full = "20080101"
            
            if start_date_full > end_date_ymd:
                continue
            
            # 为每只股票生成一个 task，包含 3 个全量 API 调用
            # 1. Tushare adj_factor API（全量复权因子）
            adj_factor_job = ApiJob(
                provider_name="tushare",
                method="get_adj_factor",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date_full,
                    "end_date": end_date_ymd,
                },
                job_id=f"{stock_id}_adj_factor_full",
                api_name="get_adj_factor"
            )
            
            # 2. Tushare daily_kline API（全量原始收盘价）
            daily_kline_job = ApiJob(
                provider_name="tushare",
                method="get_daily_kline",
                params={
                    "ts_code": stock_id,
                    "start_date": start_date_full,
                    "end_date": end_date_ymd,
                },
                job_id=f"{stock_id}_daily_kline_full",
                api_name="get_daily_kline"
            )
            
            # 3. EastMoney API（全量前复权价格）
            eastmoney_secid = AdjFactorEventHandlerHelper.convert_to_eastmoney_secid(stock_id)
            eastmoney_job = ApiJob(
                provider_name="eastmoney",
                method="get_qfq_kline",
                params={
                    "secid": eastmoney_secid,
                    "end_date": end_date_ymd,
                    "limit": 5000  # 足够大的 limit 以获取全量数据
                },
                job_id=f"{stock_id}_eastmoney_full",
                api_name="get_qfq_kline"
            )
            
            task = DataSourceTask(
                task_id=f"adj_factor_event_{stock_id}",
                api_jobs=[adj_factor_job, daily_kline_job, eastmoney_job],
                description=f"获取 {stock_id} 的全量复权因子事件数据",
            )
            tasks.append(task)
        
        logger.info(f"✅ 生成了 {len(tasks)} 个复权因子事件获取任务（以股票为单位，每只股票 3 个全量 API 调用）")
        return tasks
    
    async def after_execute(self, task_results: Dict[str, Dict[str, Any]], context: Dict[str, Any] = None):
        """
        执行后处理（步骤4）
        
        处理全量 API 返回结果，计算所有复权事件日的 qfq_diff，批量保存到数据库
        """
        context = context or {}
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化，无法保存数据")
            return
        
        adj_factor_event_model = self.data_manager.get_model('adj_factor_event')
        stock_info_map = context.get("stock_info_map", {})
        saved_count = 0
        failed_count = 0
        
        # task_results 的结构：{task_id: {job_id: result}}
        # 优化：每处理完一个 task 的结果就立即保存，而不是等所有 task 都处理完
        for task_id, task_result in task_results.items():
            if not task_result:
                failed_count += 1
                continue
            
            # 解析 task_id: adj_factor_event_{stock_id}
            if not task_id.startswith("adj_factor_event_"):
                failed_count += 1
                continue
            
            stock_id = task_id.replace("adj_factor_event_", "")
            
            try:
                # 删除该股票的旧复权事件记录，实现"全量重算"
                adj_factor_event_model.delete("id = %s", (stock_id,))
                
                # 获取三个全量 API 的结果
                adj_factor_df = task_result.get(f"{stock_id}_adj_factor_full")
                daily_kline_df = task_result.get(f"{stock_id}_daily_kline_full")
                eastmoney_result = task_result.get(f"{stock_id}_eastmoney_full")
                
                # 验证必需的数据
                if adj_factor_df is None or adj_factor_df.empty:
                    logger.warning(f"{stock_id}: 复权因子数据为空，跳过")
                    failed_count += 1
                    continue
                
                if daily_kline_df is None or daily_kline_df.empty:
                    logger.warning(f"{stock_id}: 日线数据为空，跳过")
                    failed_count += 1
                    continue
                
                # 解析 EastMoney 全量数据，构建日期 -> QFQ 价格的映射
                eastmoney_qfq_map = AdjFactorEventHandlerHelper.parse_eastmoney_qfq_price_map(eastmoney_result)
                
                # 处理日线数据，构建日期 -> 原始收盘价的映射
                raw_price_map = AdjFactorEventHandlerHelper.build_raw_price_map(daily_kline_df)
                
                # 获取第一根日线日期
                info = stock_info_map.get(stock_id, {})
                first_kline_date = info.get('first_kline_date')
                first_kline_ymd = None
                if first_kline_date:
                    first_kline_ymd = AdjFactorEventHandlerHelper.normalize_date_to_yyyymmdd(first_kline_date)
                
                # 复权因子和diff是为了股票的K线服务的，如果没有K线，因子和diff都没有存在的意义
                # 如果没有第一根K线日期，说明股票没有K线数据，直接跳过
                if not first_kline_ymd:
                    logger.warning(f"{stock_id}: 没有第一根K线数据，跳过复权因子保存（复权因子需要K线数据支持）")
                    failed_count += 1
                    continue
                
                # 构建复权因子事件列表
                events_to_save = AdjFactorEventHandlerHelper.build_adj_factor_events(
                    stock_id=stock_id,
                    adj_factor_df=adj_factor_df,
                    raw_price_map=raw_price_map,
                    eastmoney_qfq_map=eastmoney_qfq_map,
                    first_kline_ymd=first_kline_ymd
                )
                
                # 立即保存该股票的复权事件（优化：每完成一只股票就立即保存，避免中断导致数据丢失）
                # 全量更新：已删除旧数据，现在保存新的全量数据
                if events_to_save:
                    adj_factor_event_model.save_events(events_to_save)
                    saved_count += len(events_to_save)
                    logger.info(f"✅ {stock_id}: 保存了 {len(events_to_save)} 个复权事件（全量更新）")
                else:
                    logger.warning(f"{stock_id}: 没有可保存的复权事件")
                    failed_count += 1
                
            except Exception as e:
                logger.error(f"❌ 处理复权因子事件失败: {stock_id}, {e}")
                failed_count += 1
                import traceback
                traceback.print_exc()
        
        logger.info(f"✅ 复权因子事件处理完成，成功 {saved_count} 条，失败 {failed_count} 条")
    
    async def after_normalize(self, normalized_data: Dict[str, Any], context: Dict[str, Any] = None):
        """
        标准化后处理（步骤5-6）
        
        步骤5：处理新股票的第一天（已在 before_fetch 中处理）
        步骤6：季度CSV导出
        """
        context = context or {}
        
        if not self.data_manager:
            return
        
        adj_factor_event_model = self.data_manager.get_model('adj_factor_event')
        
        # ========== 步骤6：季度CSV导出 ==========
        # 检查是否需要导出CSV（每季度一次）
        # 这里简化处理：每次更新后都检查，如果当前季度还没有CSV就导出
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name()
        current_csv_path = os.path.join(adj_factor_event_model.csv_dir, current_csv_name)
        
        if not os.path.exists(current_csv_path):
            logger.info(f"📋 步骤 6/6: 导出季度CSV...")
            exported_count = adj_factor_event_model.export_to_csv()
            if exported_count > 0:
                logger.info(f"✅ 导出季度CSV完成: {exported_count} 条记录 -> {current_csv_name}")
            else:
                logger.warning("导出季度CSV失败")
        else:
            logger.debug(f"当前季度CSV已存在: {current_csv_name}")
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据（用于兼容框架，实际保存逻辑在 after_execute 中）
        """
        # 数据已在 after_execute 中保存，这里返回空数据
        return {"data": []}
