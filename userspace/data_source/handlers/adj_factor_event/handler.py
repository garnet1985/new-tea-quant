"""
复权因子事件 Handler（新算法 - 批量扫描版）

根据优化方案，实现高效的批量扫描和更新流程：
0. CSV导入（如果表为空）
1. 批量查询超过N天未更新的股票
2. 为有变化的股票生成 ApiJobs（Tushare adj_factor + daily_kline + EastMoney QFQ）
3. 保存数据
4. 季度CSV导出
"""
from typing import List, Dict, Any
from loguru import logger
import os

from core.modules.data_source.base_class.base_handler import BaseHandler
from core.modules.data_source.base_class.base_provider import BaseProvider
from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from userspace.data_source.handlers.adj_factor_event.helper import AdjFactorEventHandlerHelper as helper
from core.utils.date.date_utils import DateUtils
from core.infra.project_context import ConfigManager


class AdjFactorEventHandler(BaseHandler):
    """
    复权因子事件 Handler（新算法 - 批量扫描版）
    
    特点：
    - CSV缓存：空表时从CSV快速恢复
    - 批量筛选：一次SQL查询找出需要更新的股票
    - 多线程支持：预筛选和精确计算都支持多线程
    - 季度CSV导出：定期备份数据
    """
    
    def __init__(self, data_source_key: str, schema, config, providers: Dict[str, BaseProvider]):
        super().__init__(data_source_key, schema, config, providers)
        
        # 用于跟踪任务完成状态
        self._total_stocks = 0
        self._completed_stocks = 0
        self._tasks_incomplete = False
    
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        """
        抓取前阶段钩子：筛选需要更新的股票，为每个股票创建 3 个 ApiJob
        
        Args:
            context: 执行上下文
            apis: 原始 ApiJob 列表（从 config 构建）
            
        Returns:
            List[ApiJob]: 处理后的 ApiJob 列表（每个股票 3 个 ApiJob）
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化")
            return apis
        
        # 获取股票列表
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("股票列表为空，无法创建复权因子事件获取任务")
            return apis
        
        # 获取最新完成交易日
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date:
            try:
                latest_completed_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新完成交易日失败: {e}")
                return apis
        
        # 记录本轮执行对应的最新完成交易日，用于后续季度 CSV 命名
        self._latest_completed_trading_date = latest_completed_trading_date
        
        # 使用 service 访问 model
        adj_factor_event_model = data_manager.stock.kline._adj_factor_event
        
        # ========== 步骤0：根据 DB / CSV 状态做初始化决策 ==========
        context["should_generate_csv"] = False
        is_table_empty = adj_factor_event_model.is_table_empty()
        
        if is_table_empty:
            # 表为空：尝试从 CSV 恢复
            if self._is_csv_exist_and_valid(adj_factor_event_model):
                imported_count = adj_factor_event_model.import_from_csv()
                if imported_count > 0:
                    logger.info(f"✅ 从CSV导入 {imported_count} 条记录，表已恢复")
                    is_table_empty = False
                else:
                    logger.warning("CSV导入失败或无数据")
            else:
                logger.info("表为空且无有效CSV，将进行首次构建")
        else:
            # 表不为空：检查是否需要生成新的 CSV
            if self._is_csv_expired(adj_factor_event_model, base_date=latest_completed_trading_date) or not self._is_csv_exist_and_valid(adj_factor_event_model):
                context["should_generate_csv"] = True
                logger.info("CSV已过期或不存在，将在更新后生成新CSV")
        
        # ========== 步骤1：为所有股票创建 ApiJobs ==========
        # 注意：框架会在 on_before_fetch 之后根据 renew_if_over_days 配置自动过滤不需要更新的股票
        # 这里我们为所有股票创建 ApiJobs，框架会自动处理阈值过滤
        
        # 构建 API name 到 base_api 的映射
        api_map = {api.api_name: api for api in apis}
        
        expanded_apis = []
        default_start_date = ConfigManager.get_default_start_date()
        end_date_ymd = latest_completed_trading_date
        
        # 为所有股票创建 ApiJobs（框架会自动过滤）
        for stock in stock_list:
            stock_id = stock.get('id') or stock.get('ts_code')
            if not stock_id:
                continue
            
            # 1. Tushare adj_factor API（全量复权因子）
            adj_factor_api = api_map.get("adj_factor")
            if adj_factor_api:
                expanded_apis.append(ApiJob(
                    api_name=adj_factor_api.api_name,
                    provider_name=adj_factor_api.provider_name,
                    method=adj_factor_api.method,
                    params={
                        **adj_factor_api.params,
                        "ts_code": stock_id,
                        "start_date": default_start_date,
                        "end_date": end_date_ymd,
                    },
                    api_params=adj_factor_api.api_params,
                    depends_on=adj_factor_api.depends_on,
                    rate_limit=adj_factor_api.rate_limit,
                    job_id=f"{stock_id}_adj_factor_full",
                ))
            
            # 2. Tushare daily_kline API（全量原始收盘价）
            daily_kline_api = api_map.get("daily_kline")
            if daily_kline_api:
                expanded_apis.append(ApiJob(
                    api_name=daily_kline_api.api_name,
                    provider_name=daily_kline_api.provider_name,
                    method=daily_kline_api.method,
                    params={
                        **daily_kline_api.params,
                        "ts_code": stock_id,
                        "start_date": default_start_date,
                        "end_date": end_date_ymd,
                    },
                    api_params=daily_kline_api.api_params,
                    depends_on=daily_kline_api.depends_on,
                    rate_limit=daily_kline_api.rate_limit,
                    job_id=f"{stock_id}_daily_kline_full",
                ))
            
            # 3. EastMoney API（全量前复权价格）
            qfq_kline_api = api_map.get("qfq_kline")
            if qfq_kline_api:
                eastmoney_secid = helper.convert_to_eastmoney_secid(stock_id)
                expanded_apis.append(ApiJob(
                    api_name=qfq_kline_api.api_name,
                    provider_name=qfq_kline_api.provider_name,
                    method=qfq_kline_api.method,
                    params={
                        **qfq_kline_api.params,
                        "secid": eastmoney_secid,
                        "start_date": default_start_date,
                        "end_date": end_date_ymd,
                    },
                    api_params=qfq_kline_api.api_params,
                    depends_on=qfq_kline_api.depends_on,
                    rate_limit=qfq_kline_api.rate_limit,
                    job_id=f"{stock_id}_eastmoney_full",
                ))
        
        logger.info(f"✅ 为 {len(stock_list)} 只股票生成了复权因子事件获取任务，共 {len(expanded_apis)} 个 ApiJob（框架会自动过滤不需要更新的股票）")
        return expanded_apis
    
    def on_after_execute_job_batch_for_single_stock(
        self, 
        context: Dict[str, Any],
        job_bundle: ApiJobBundle, 
        fetched_data: Dict[str, Any]
    ):
        """
        执行 job batch 后的钩子：按股票分组保存数据
        
        由于基类将所有 apis 打包成一个 batch，我们需要在这里按股票分组处理数据
        
        注意：此处的保存逻辑是按实体（股票）逐个保存，属于执行期保存模式。
        如果未来需要将 save 逻辑完全抽离到上层，可以移除此处的保存调用。
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            logger.warning("DataManager 未初始化，无法保存复权因子事件数据")
            return
        
        # 按股票分组处理数据
        stock_jobs_map = {}  # {stock_id: {job_id: result}}
        
        # 构建 job_id 到 stock_id 的映射
        for api_job in job_bundle.apis:
            job_id = api_job.job_id
            if not job_id:
                continue
            
            # 解析 stock_id（job_id 格式：{stock_id}_adj_factor_full 或 {stock_id}_daily_kline_full 或 {stock_id}_eastmoney_full）
            if "_adj_factor_full" in job_id:
                stock_id = job_id.replace("_adj_factor_full", "")
            elif "_daily_kline_full" in job_id:
                stock_id = job_id.replace("_daily_kline_full", "")
            elif "_eastmoney_full" in job_id:
                stock_id = job_id.replace("_eastmoney_full", "")
            else:
                continue
            
            if stock_id not in stock_jobs_map:
                stock_jobs_map[stock_id] = {}
            
            result = fetched_data.get(job_id)
            if result is not None:
                stock_jobs_map[stock_id][job_id] = result
        
        # 保存每个股票的数据
        for stock_id, stock_results in stock_jobs_map.items():
            try:
                self._save_stock_adj_factor_events(data_manager, stock_id, stock_results)
                self._completed_stocks += 1
            except Exception as e:
                logger.error(f"❌ 保存股票 {stock_id} 复权因子事件失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # 更新总股票数（用于 CSV 导出判断，基于实际执行的股票数）
        if not hasattr(self, '_total_stocks') or self._total_stocks == 0:
            self._total_stocks = len(stock_jobs_map)
        
        # 更新总股票数（用于 CSV 导出判断）
        if not hasattr(self, '_total_stocks') or self._total_stocks == 0:
            self._total_stocks = len(stock_jobs_map)
    
    def _save_stock_adj_factor_events(
        self,
        data_manager,
        stock_id: str,
        stock_results: Dict[str, Any]
    ):
        """
        保存单个股票的复权因子事件数据
        
        Args:
            data_manager: DataManager 实例
            stock_id: 股票代码
            stock_results: {job_id: result} 格式的数据
        """
        # 使用 service 访问 model
        adj_factor_event_model = data_manager.stock.kline._adj_factor_event
        
        # 删除该股票的旧复权事件记录，实现"全量重算"
        data_manager.stock.kline.delete_adj_factor_events(stock_id)
        
        # 获取三个全量 API 的结果
        adj_factor_df = stock_results.get(f"{stock_id}_adj_factor_full")
        daily_kline_df = stock_results.get(f"{stock_id}_daily_kline_full")
        eastmoney_result = stock_results.get(f"{stock_id}_eastmoney_full")
        
        # 验证必需的数据
        if adj_factor_df is None or (hasattr(adj_factor_df, 'empty') and adj_factor_df.empty):
            logger.warning(f"{stock_id}: 复权因子数据为空，跳过")
            return
        
        if daily_kline_df is None or (hasattr(daily_kline_df, 'empty') and daily_kline_df.empty):
            logger.warning(f"{stock_id}: 日线数据为空，跳过")
            return
        
        # 解析 EastMoney 全量数据，构建日期 -> QFQ 价格的映射
        eastmoney_qfq_map = helper.parse_eastmoney_qfq_price_map(eastmoney_result)
        
        # 处理日线数据，构建日期 -> 原始收盘价的映射
        raw_price_map = helper.build_raw_price_map(daily_kline_df)
        
        # 获取第一根日线日期
        first_kline_ymd = None
        
        # 1. 优先从 EastMoney 获取第一个K线日期
        if eastmoney_qfq_map:
            first_eastmoney_date = min(eastmoney_qfq_map.keys())
            first_kline_ymd = first_eastmoney_date
        
        # 2. 如果 EastMoney 没有数据，从 daily_kline_df 获取
        if not first_kline_ymd and not (hasattr(daily_kline_df, 'empty') and daily_kline_df.empty):
            import pandas as pd
            if isinstance(daily_kline_df, pd.DataFrame) and 'trade_date' in daily_kline_df.columns:
                first_kline_date = daily_kline_df['trade_date'].min()
                first_kline_ymd = helper.normalize_date_to_yyyymmdd(str(first_kline_date))
        
        # 复权因子和diff是为了股票的K线服务的，如果没有K线，因子和diff都没有存在的意义
        if not first_kline_ymd:
            logger.warning(f"{stock_id}: 没有第一根K线数据（EastMoney 和 daily_kline 都没有数据），跳过复权因子保存")
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
            count = data_manager.stock.kline.save_adj_factor_events(events_to_save)
            logger.info(f"✅ [全量替换] {stock_id}: 保存了 {len(events_to_save)} 个复权事件（实际保存 {count} 条）")
        else:
            logger.warning(f"{stock_id}: 没有可保存的复权事件")
    
    def _is_table_empty(self, adj_factor_event_model) -> bool:
        """检查复权因子事件表是否为空"""
        return adj_factor_event_model.is_table_empty()
    
    def _is_csv_exist_and_valid(self, adj_factor_event_model) -> bool:
        """检查CSV文件是否存在且有效"""
        csv_file = adj_factor_event_model.get_latest_csv_file()
        if not csv_file or not os.path.exists(csv_file):
            return False
        
        try:
            import pandas as pd
            df = pd.read_csv(csv_file, nrows=1)
            required_columns = ['id', 'event_date', 'factor', 'qfq_diff']
            return all(col in df.columns for col in required_columns)
        except Exception:
            return False
    
    def _is_csv_expired(self, adj_factor_event_model, base_date: str = None) -> bool:
        """检查CSV文件是否过期（超过一个季度）"""
        csv_file = adj_factor_event_model.get_latest_csv_file()
        if not csv_file:
            return True
        
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name(base_date=base_date)
        csv_name = os.path.basename(csv_file)
        return csv_name != current_csv_name
    
    def _get_last_updated_dates(self, adj_factor_event_model) -> Dict[str, str]:
        """获取每只股票的最后更新时间（last_update）"""
        try:
            query = f"""
                SELECT id, MAX(last_update) as latest_last_update
                FROM {adj_factor_event_model.table_name}
                GROUP BY id
            """
            results = adj_factor_event_model.db.execute_sync_query(query)
            result_dict = {}
            for row in results:
                if row.get('latest_last_update'):
                    latest_update = row['latest_last_update']
                    from datetime import datetime
                    if isinstance(latest_update, datetime):
                        latest_date_str = latest_update.strftime('%Y%m%d')
                    elif isinstance(latest_update, str):
                        try:
                            dt = datetime.strptime(latest_update, '%Y-%m-%d %H:%M:%S')
                            latest_date_str = dt.strftime('%Y%m%d')
                        except:
                            latest_date_str = latest_update.replace('-', '').replace(' ', '').replace(':', '')[:8]
                    else:
                        latest_date_str = str(latest_update).replace('-', '').replace(' ', '').replace(':', '')[:8]
                    result_dict[row['id']] = latest_date_str
            return result_dict
        except Exception as e:
            logger.error(f"获取最后更新日期失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def _normalize_data(self, context: Dict[str, Any], fetched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化数据：覆盖基类方法，因为数据已经在 on_after_execute_job_batch_for_single_stock 中保存
        
        这里只返回空数据，避免重复处理
        """
        # 数据已经在 on_after_execute_job_batch_for_single_stock 中按股票逐个保存
        # 这里不需要再次处理，返回空数据即可
        return {"data": []}
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：季度CSV导出
        
        步骤6：季度CSV导出（仅在所有任务完成且写入落盘之后）
        """
        data_manager = context.get("data_manager")
        if not data_manager:
            return normalized_data
        
        # 检查任务是否全部完成
        if self._completed_stocks < self._total_stocks:
            self._tasks_incomplete = True
            logger.warning(
                f"⚠️ 复权因子事件任务未全部完成: 成功 {self._completed_stocks}/{self._total_stocks}，跳过季度CSV导出"
            )
            return normalized_data
        
        # 使用 service 访问 model
        adj_factor_event_model = data_manager.stock.kline._adj_factor_event
        
        # 检查是否需要导出CSV
        base_date = getattr(self, "_latest_completed_trading_date", None)
        current_csv_name = adj_factor_event_model.get_current_quarter_csv_name(base_date=base_date)
        current_csv_path = os.path.join(adj_factor_event_model.csv_dir, current_csv_name)
        
        if not os.path.exists(current_csv_path):
            logger.info("📋 步骤 6/6: 导出季度CSV...")
            exported_count = adj_factor_event_model.export_to_csv(file_path=current_csv_path)
            if exported_count > 0:
                logger.info(f"✅ 导出季度CSV完成: {exported_count} 条记录 -> {current_csv_name}")
            else:
                logger.warning("导出季度CSV失败")
        else:
            logger.debug(f"当前季度CSV已存在: {current_csv_name}")
        
        return normalized_data
