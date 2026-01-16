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

from core.modules.data_source.data_source_handler import BaseDataSourceHandler
from core.modules.data_source.api_job import DataSourceTask, ApiJob
from userspace.data_source.handlers.adj_factor_event.helper import AdjFactorEventHandlerHelper as helper
from core.utils.date.date_utils import DateUtils


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
    description = "获取复权因子事件数据（只存储除权日）"
    dependencies = []  # 依赖：无

    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params or {}, data_manager)
        # 从 params 读取配置
        self.update_threshold_days = params.get('update_threshold_days', 15)  # 默认15天
        self.max_workers = params.get('max_workers', 10)  # 最大线程数
    
    def _is_table_empty(self, adj_factor_event_model) -> bool:
        """
        检查复权因子事件表是否为空
        
        Args:
            adj_factor_event_model: AdjFactorEventModel 实例
            
        Returns:
            bool: 表为空返回 True
        """
        return adj_factor_event_model.is_table_empty()
    
    def _is_csv_exist_and_valid(self, adj_factor_event_model) -> bool:
        """
        检查CSV文件是否存在且有效（文件存在且格式正确）
        
        Args:
            adj_factor_event_model: AdjFactorEventModel 实例
            
        Returns:
            bool: CSV存在且有效返回 True
        """
        csv_file = adj_factor_event_model.get_latest_csv_file()
        if not csv_file or not os.path.exists(csv_file):
            return False
        
        # 检查文件是否可读且非空
        try:
            import pandas as pd
            df = pd.read_csv(csv_file, nrows=1)  # 只读第一行检查格式
            required_columns = ['id', 'event_date', 'factor', 'qfq_diff']
            return all(col in df.columns for col in required_columns)
        except Exception:
            return False
    
    def _is_csv_expired(self, adj_factor_event_model, base_date: str = None) -> bool:
        """
        检查CSV文件是否过期（超过一个季度）
        
        Args:
            adj_factor_event_model: AdjFactorEventModel 实例
            base_date: 基准日期（通常是 latest_completed_trading_date，YYYYMMDD）
            
        Returns:
            bool: CSV过期返回 True
        """
        csv_file = adj_factor_event_model.get_latest_csv_file()
        if not csv_file:
            return True  # 不存在视为过期
        
        # 获取当前季度CSV文件名（基于 base_date 计算“已完成的上个季度”）
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name(base_date=base_date)
        csv_name = os.path.basename(csv_file)
        
        # 如果文件名不是当前季度的，视为过期
        return csv_name != current_csv_name
    
    def _get_last_updated_dates(self, adj_factor_event_model) -> Dict[str, str]:
        """
        获取每只股票的最后更新时间（last_update）
        
        注意：这里使用的是 last_update 字段（DATETIME 类型），表示记录的最后更新时间，
        而不是 event_date（除权日期）。用于判断是否需要更新数据。
        
        Args:
            adj_factor_event_model: AdjFactorEventModel 实例
            
        Returns:
            Dict[str, str]: {stock_id: latest_last_update}，格式为 YYYYMMDD
        """
        try:
            # 使用 SQL 查询每个股票的最新 last_update 时间
            # last_update 是 DATETIME 类型，MAX() 返回 datetime 对象
            query = f"""
                SELECT id, MAX(last_update) as latest_last_update
                FROM {adj_factor_event_model.table_name}
                GROUP BY id
            """
            results = adj_factor_event_model.db.execute_sync_query(query)
            # 将 datetime 对象转换为 YYYYMMDD 格式的字符串
            result_dict = {}
            for row in results:
                if row.get('latest_last_update'):
                    latest_update = row['latest_last_update']
                    # last_update 是 DATETIME 类型，返回的是 datetime 对象
                    from datetime import datetime
                    if isinstance(latest_update, datetime):
                        latest_date_str = latest_update.strftime('%Y%m%d')
                    elif isinstance(latest_update, str):
                        # 如果是字符串，尝试解析并转换
                        try:
                            dt = datetime.strptime(latest_update, '%Y-%m-%d %H:%M:%S')
                            latest_date_str = dt.strftime('%Y%m%d')
                        except:
                            # 如果解析失败，尝试移除分隔符
                            latest_date_str = latest_update.replace('-', '').replace(' ', '').replace(':', '')[:8]
                    else:
                        # 其他类型，转换为字符串后处理
                        latest_date_str = str(latest_update).replace('-', '').replace(' ', '').replace(':', '')[:8]
                    result_dict[row['id']] = latest_date_str
            return result_dict
        except Exception as e:
            logger.error(f"获取最后更新日期失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def _get_refresh_target_list(
        self, 
        stock_list: List[Dict[str, Any]], 
        last_updated_dates: Dict[str, str], 
        latest_completed_trading_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取需要更新的股票列表（带起始日期信息）
        
        筛选逻辑：
        1. 新股票：在 stock_list 中但不在 last_updated_dates 中的股票
        2. 过期股票：最后更新日期距离 latest_completed_trading_date 超过 update_threshold_days 的股票
        
        Args:
            stock_list: 股票列表（从 context 传入或从数据库加载）
            last_updated_dates: 每只股票的最后更新日期映射
            latest_completed_trading_date: 最新完成交易日（YYYYMMDD）
            
        Returns:
            List[Dict]: 需要更新的股票列表，每个元素包含：
                - stock_id: 股票代码
                - start_date: 起始日期（YYYYMMDD），用于API调用
        """
        if not stock_list:
            return []
        
        target_list = []
        latest_date = DateUtils.parse_yyyymmdd(latest_completed_trading_date)
        
        for stock in stock_list:
            stock_id = stock.get('id') or stock.get('ts_code')
            if not stock_id:
                continue
            
            # 检查是否是新股票（从未更新过）
            if stock_id not in last_updated_dates:
                # 新股票：从默认起始日期开始
                target_list.append({
                    'stock_id': stock_id
                })
                continue
            
            # 已有记录的股票：检查是否超过更新阈值
            last_update_date = DateUtils.parse_yyyymmdd(last_updated_dates[stock_id]) if last_updated_dates[stock_id] else None
            if last_update_date and (latest_date - last_update_date).days >= self.update_threshold_days:
                target_list.append({
                    'stock_id': stock_id
                })
        
        return target_list

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
        
        # 使用 service 访问（虽然目前没有对应的 service 方法，但可以通过 kline service 访问 model）
        adj_factor_event_model = self.data_manager.stock.kline._adj_factor_event
        
        # 从 context 获取最新完成交易日（优先从 context 读取，由 renew_data() 统一获取并注入）
        latest_completed_trading_date = context.get("latest_completed_trading_date") or context.get("latest_trading_date")
        if not latest_completed_trading_date:
            # 兜底：如果 context 中没有，才自己获取（不应该发生，但保留兜底逻辑）
            logger.warning("AdjFactorEventHandler.before_fetch: context 中未找到 latest_completed_trading_date，回退获取")
            latest_completed_trading_date = self.data_manager.service.calendar.get_latest_completed_trading_date()
        
        stock_list = context.get("stock_list", [])
        
        # 记录本轮执行对应的最新完成交易日，用于后续季度 CSV 命名
        self._latest_completed_trading_date = latest_completed_trading_date

        # ========== 步骤0：根据 DB / CSV 状态做初始化决策 ==========
        
        # step 1: decide csv actions: need to renew? need to import?
        context["should_generate_csv"] = False
        is_table_empty = adj_factor_event_model.is_table_empty()
        
        if is_table_empty:
            # 表为空：尝试从 CSV 恢复（但只导入未过期的 CSV）
            if self._is_csv_exist_and_valid(adj_factor_event_model):
                # CSV 存在、有效且未过期，可以导入
                imported_count = adj_factor_event_model.import_from_csv()
                if imported_count > 0:
                    logger.info(f"✅ 从CSV导入 {imported_count} 条记录，表已恢复")
                    is_table_empty = False  # 导入后表不再为空
                else:
                    logger.warning("CSV导入失败或无数据")
            else:
                logger.info("表为空且无有效CSV，将进行首次构建")
        else:
            # 表不为空：检查是否需要生成新的 CSV
            if self._is_csv_expired(adj_factor_event_model, base_date=latest_completed_trading_date) or not self._is_csv_exist_and_valid(adj_factor_event_model):
                context["should_generate_csv"] = True
                logger.info("CSV已过期或不存在，将在更新后生成新CSV")

        # ========== 步骤1：获取需要更新的股票列表 ==========
        # 获取每只股票的最后更新日期
        last_updated_dates = self._get_last_updated_dates(adj_factor_event_model)
        
        # 筛选出需要更新的股票列表（新股票 + 超过阈值的股票）
        target_list = self._get_refresh_target_list(
            stock_list, 
            last_updated_dates, 
            latest_completed_trading_date
        )
        
        context["target_stock_list"] = target_list
        context["latest_completed_trading_date"] = latest_completed_trading_date
        
        logger.info(f"✅ 筛选出 {len(target_list)} 只股票需要更新复权因子事件")
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
        target_stock_list = context.get("target_stock_list", [])
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        
        if not target_stock_list:
            logger.info("没有股票有复权事件，无需生成 tasks")
            return []
        
        tasks = []
        # latest_completed_trading_date 从顶层 context 传入，格式已统一为 YYYYMMDD
        end_date_ymd = latest_completed_trading_date
        
        # 默认起始日期（用于所有 API）
        from core.infra.project_context import ConfigManager
        default_start_date = ConfigManager.get_default_start_date()
        
        for stock_info in target_stock_list:
            stock_id = stock_info['stock_id']
            
            # 为每只股票生成一个 task，包含 3 个全量 API 调用
            # 1. Tushare adj_factor API（全量复权因子）
            adj_factor_job = ApiJob(
                provider_name="tushare",
                method="get_adj_factor",
                params={
                    "ts_code": stock_id,
                    "start_date": default_start_date,
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
                    "start_date": default_start_date,
                    "end_date": end_date_ymd,
                },
                job_id=f"{stock_id}_daily_kline_full",
                api_name="get_daily_kline"
            )
            
            # 3. EastMoney API（全量前复权价格）
            # 注意：EastMoney API 支持 start_date 参数（起始日期，YYYYMMDD 格式）
            # 当提供 start_date 时，API 内部会使用 beg 参数，且不会使用 lmt 参数
            eastmoney_secid = helper.convert_to_eastmoney_secid(stock_id)
            eastmoney_job = ApiJob(
                provider_name="eastmoney",
                method="get_qfq_kline",
                params={
                    "secid": eastmoney_secid,
                    "start_date": default_start_date,  # 起始日期（Provider 内部会转换为 beg 参数）
                    "end_date": end_date_ymd,           # 结束日期
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

    async def before_all_tasks_execute(self, tasks: List[DataSourceTask], context: Dict[str, Any] = None):
        """
        所有 tasks 执行前的钩子：记录总任务数，用于后续统计与安全检查
        """
        # 记录本次期望执行的任务总数
        self._total_tasks = len(tasks)
        # 每次执行前重置完成计数与标记
        self._completed_tasks = 0
        self._tasks_incomplete = False
    
    async def after_single_task_execute(
        self,
        task_id: str,
        task_result: Dict[str, Any],
        context: Dict[str, Any] = None
    ):
        """
        单个 task 执行后的钩子（用于增量保存）
        
        框架会在每个 task 执行完成后立即调用此方法，实现断点续传能力。
        
        Args:
            task_id: 任务ID（格式：adj_factor_event_{stock_id}）
            task_result: 任务执行结果 {job_id: result}
            context: 执行上下文，可能包含 dry_run 标志
        """
        context = context or {}
        
        # 检查是否是 dry_run 模式
        dry_run = context.get('dry_run', False)
        if dry_run:
            logger.debug(f"[增量保存] 干运行模式，跳过任务 {task_id}")
            return
        
        if not self.data_manager:
            logger.warning(f"[增量保存] data_manager 未设置，无法保存任务 {task_id}")
            return
        
        # 解析 task_id: adj_factor_event_{stock_id}
        if not task_id.startswith("adj_factor_event_"):
            logger.debug(f"[增量保存] 任务 {task_id} 格式不正确，跳过")
            return
        
        stock_id = task_id.replace("adj_factor_event_", "")
        
        try:
            # 使用 service 访问（虽然目前没有对应的 service 方法，但可以通过 kline service 访问 model）
            adj_factor_event_model = self.data_manager.stock.kline._adj_factor_event
            
            # 删除该股票的旧复权事件记录，实现"全量重算"
            self.data_manager.stock.kline.delete_adj_factor_events(stock_id)
            
            # 获取三个全量 API 的结果
            adj_factor_df = task_result.get(f"{stock_id}_adj_factor_full")
            daily_kline_df = task_result.get(f"{stock_id}_daily_kline_full")
            eastmoney_result = task_result.get(f"{stock_id}_eastmoney_full")
            
            # 验证必需的数据
            if adj_factor_df is None or adj_factor_df.empty:
                logger.warning(f"{stock_id}: 复权因子数据为空，跳过")
                return
            
            if daily_kline_df is None or daily_kline_df.empty:
                logger.warning(f"{stock_id}: 日线数据为空，跳过")
                return
            
            # 解析 EastMoney 全量数据，构建日期 -> QFQ 价格的映射
            eastmoney_qfq_map = helper.parse_eastmoney_qfq_price_map(eastmoney_result)
            
            # 处理日线数据，构建日期 -> 原始收盘价的映射
            raw_price_map = helper.build_raw_price_map(daily_kline_df)
            
            # 获取第一根日线日期
            # 优先使用 EastMoney 的第一个K线日期（因为复权因子依赖 EastMoney 的前复权价格）
            # 如果 EastMoney 没有数据，则使用 daily_kline 的第一根日期
            first_kline_ymd = None
            
            # 1. 优先从 EastMoney 获取第一个K线日期（因为复权因子依赖 EastMoney）
            if eastmoney_qfq_map:
                first_eastmoney_date = min(eastmoney_qfq_map.keys())
                first_kline_ymd = first_eastmoney_date
            
            # 2. 如果 EastMoney 没有数据，从 daily_kline_df 获取
            if not first_kline_ymd and not daily_kline_df.empty:
                import pandas as pd
                if 'trade_date' in daily_kline_df.columns:
                    first_kline_date = daily_kline_df['trade_date'].min()
                    first_kline_ymd = helper.normalize_date_to_yyyymmdd(str(first_kline_date))
            
            # 复权因子和diff是为了股票的K线服务的，如果没有K线，因子和diff都没有存在的意义
            if not first_kline_ymd:
                logger.warning(f"{stock_id}: 没有第一根K线数据（EastMoney 和 daily_kline 都没有数据），跳过复权因子保存（复权因子需要K线数据支持）")
                return
            
            # 构建复权因子事件列表
            events_to_save = helper.build_adj_factor_events(
                stock_id=stock_id,
                adj_factor_df=adj_factor_df,
                raw_price_map=raw_price_map,
                eastmoney_qfq_map=eastmoney_qfq_map,
                first_kline_ymd=first_kline_ymd
            )
            
            # 立即保存该股票的复权事件（全量替换：先删除再保存，每完成一只股票就立即保存）
            if events_to_save:
                # 使用 service 保存数据
                count = self.data_manager.stock.kline.save_adj_factor_events(events_to_save)
                logger.info(f"✅ [全量替换] {stock_id}: 保存了 {len(events_to_save)} 个复权事件（实际保存 {count} 条）")
            else:
                logger.warning(f"{stock_id}: 没有可保存的复权事件")
                
        except Exception as e:
            logger.error(f"❌ [增量保存] 任务 {task_id} 保存失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def after_all_tasks_execute(self, task_results: Dict[str, Dict[str, Any]], context: Dict[str, Any] = None):
        """
        所有 tasks 执行完成后的回调（框架接口：after_all_tasks_execute）
        
        注意：此方法在所有 tasks 执行完成后统一调用。
        如果实现了 after_single_task_execute，数据已在每个 task 完成时保存，
        这里主要用于统计、日志记录等后处理工作。
        
        Args:
            task_results: 所有 task 的执行结果 {task_id: {job_id: result}}
            context: 执行上下文
        """
        context = context or {}
        
        if not self.data_manager:
            logger.warning("DataManager 未初始化")
            return
        
        # 记录完成任务数，并与期望任务数对比
        completed_tasks = len(task_results)
        total_tasks = getattr(self, "_total_tasks", completed_tasks)
        self._completed_tasks = completed_tasks
        
        if completed_tasks < total_tasks:
            # 标记本次执行不完整，后续流程（如 CSV 导出）需要避免认为是“全量完成”
            self._tasks_incomplete = True
            logger.warning(
                f"⚠️ 复权因子事件任务未全部完成: 成功 {completed_tasks}/{total_tasks} "
                f"(可能存在失败或超时任务)"
            )
        else:
            self._tasks_incomplete = False
            logger.info(f"✅ 所有复权因子事件任务执行完成，共 {completed_tasks} 个任务")
        
        # CSV 导出逻辑在 after_normalize 中完成
    
    async def after_normalize(self, normalized_data: Dict[str, Any]):
        """
        标准化后处理（步骤5-6）
        
        步骤5：处理新股票的第一天（已在 before_fetch 中处理）
        步骤6：季度CSV导出（仅在所有任务完成且写入落盘之后）
        """
        if not self.data_manager:
            return
        
        # 使用 service 访问（虽然目前没有对应的 service 方法，但可以通过 kline service 访问 model）
        adj_factor_event_model = self.data_manager.stock.kline._adj_factor_event
        
        # 如果本次任务未全部成功完成，避免导出不完整的 CSV
        if getattr(self, "_tasks_incomplete", False):
            logger.warning(
                "检测到本次复权因子事件任务未全部完成，跳过季度CSV导出以避免导出不完整数据"
            )
            return
        
        # 在导出 CSV 前，确保所有数据已写入数据库
        # 注意：数据库写入是同步的，无需额外等待
        
        # ========== 步骤6：季度CSV导出 ==========
        # 检查是否需要导出CSV（每季度一次）
        # 使用 latest_completed_trading_date 所在季度的“上一个完整季度”作为文件名中的季度
        base_date = getattr(self, "_latest_completed_trading_date", None)
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name(base_date=base_date)
        current_csv_path = os.path.join(adj_factor_event_model.csv_dir, current_csv_name)
        
        if not os.path.exists(current_csv_path):
            logger.info("📋 步骤 6/6: 导出季度CSV...")
            # 显式传入目标路径，避免在 Model 内部重新计算季度名称
            exported_count = adj_factor_event_model.export_to_csv(file_path=current_csv_path)
            if exported_count > 0:
                logger.info(f"✅ 导出季度CSV完成: {exported_count} 条记录 -> {current_csv_name}")
            else:
                logger.warning("导出季度CSV失败")
        else:
            logger.debug(f"当前季度CSV已存在: {current_csv_name}")
    
    async def normalize(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        标准化数据（实际保存逻辑在 after_all_tasks_execute 中）
        """
        # 数据已在 after_all_tasks_execute 中保存，这里返回空数据
        return {"data": []}
