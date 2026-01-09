#!/usr/bin/env python3
"""
Opportunity Enumerator Worker - 枚举器 Worker

职责：
- 在子进程中运行
- 枚举单个股票的所有投资机会
- 同时追踪多个 opportunities（可重叠）
- 每个 opportunity 独立 track 到完成
"""

from typing import Dict, Any, List
import logging
import time

logger = logging.getLogger(__name__)


class OpportunityEnumeratorWorker:
    """枚举器 Worker（子进程）"""
    
    def __init__(self, job_payload: Dict[str, Any]):
        """
        初始化枚举器 Worker
        
        Args:
            job_payload: 作业负载，包含：
                - stock_id: 股票代码
                - strategy_name: 策略名称
                - settings: 策略配置字典
                - start_date: 开始日期
                - end_date: 结束日期
        """
        self.job_payload = job_payload
        
        # 提取基本信息
        self.stock_id = job_payload['stock_id']
        self.strategy_name = job_payload['strategy_name']
        self.start_date = job_payload['start_date']
        self.end_date = job_payload['end_date']
        
        # 解析配置
        from app.core.modules.strategy.models.strategy_settings import StrategySettings
        self.settings = StrategySettings.from_dict(job_payload['settings'])
        
        # 初始化数据管理器
        from app.core.modules.data_manager import DataManager
        self.data_mgr = DataManager(is_verbose=False)
        
        # 加载完整的股票信息（提前组织好，避免每次创建 Opportunity 时重复查询）
        self.stock_info = self._load_stock_info()
        
        from app.core.modules.strategy.components.strategy_worker_data_manager import StrategyWorkerDataManager
        self.data_manager = StrategyWorkerDataManager(
            stock_id=self.stock_id,
            settings=self.settings,
            data_mgr=self.data_mgr
        )
        
        # 动态导入用户策略
        self._load_user_strategy()
    
    def _load_stock_info(self) -> Dict[str, Any]:
        """
        加载股票信息（枚举器版本）
        
        说明：
        - 为了避免在多进程环境下对 stock_list 频繁 DB 访问导致
          MySQL 'Command Out of Sync' 错误，这里不再访问数据库，
          只返回最小必要字段。
        - 如果将来需要更丰富的元信息，可以在主进程预加载后通过 job_payload 传入。
        """
        return {
            "id": self.stock_id,
            "name": self.stock_id,
            "industry": "",
            "type": "",
            "exchange_center": "",
        }
    
    def _load_user_strategy(self):
        """动态加载用户策略"""
        import importlib
        import inspect
        from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
        
        module_path = f"app.userspace.strategies.{self.strategy_name}.strategy_worker"
        try:
            module = importlib.import_module(module_path)
            
            # 尝试多种类名查找方式
            strategy_class = None
            
            # 1. 尝试查找 'StrategyWorker'
            if hasattr(module, 'StrategyWorker'):
                strategy_class = getattr(module, 'StrategyWorker')
            # 2. 尝试查找 '{StrategyName}StrategyWorker'（首字母大写）
            else:
                strategy_name_capitalized = self.strategy_name.capitalize()
                class_name = f"{strategy_name_capitalized}StrategyWorker"
                if hasattr(module, class_name):
                    strategy_class = getattr(module, class_name)
            # 3. 如果还找不到，查找所有继承自 BaseStrategyWorker 的类
            if strategy_class is None:
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseStrategyWorker) and 
                        obj != BaseStrategyWorker):
                        strategy_class = obj
                        break
            
            if strategy_class is None:
                raise ValueError(f"找不到策略类: {module_path}")
            
            # 创建一个临时实例来获取 scan_opportunity 方法
            dummy_payload = {
                'stock_id': self.stock_id,
                'execution_mode': 'scan',
                'strategy_name': self.strategy_name,
                'settings': self.settings.to_dict()
            }
            self.strategy_instance = strategy_class(dummy_payload)
            
            # 将预加载的股票信息传递给策略实例（如果它需要）
            if hasattr(self.strategy_instance, 'stock_info'):
                self.strategy_instance.stock_info = self.stock_info
            
        except Exception as e:
            logger.error(f"加载策略失败: {self.strategy_name}, error={e}")
            raise
    
    def run(self) -> Dict[str, Any]:
        """
        运行枚举器（子进程入口）
        
        说明：
        - 枚举器（Layer 0）始终做“全量历史枚举”，当前 Worker 接收到的 start_date
          已经是全局 DEFAULT_START_DATE，由 OpportunityEnumerator 统一控制。
        - lookback 只影响“从哪一天开始对用户策略生效”（前面作为预热窗口），
          不影响加载的数据范围。
        
        Returns:
            {
                'success': True/False,
                'stock_id': '000001.SZ',
                'opportunity_count': int
            }
        """
        t_start = time.perf_counter()
        try:
            # 1. 计算真正的开始日期（需要预留 lookback 窗口）
            # 使用 min_required_records 作为 lookback，但限制最大为 60 天。
            # 注意：这里仅用于“预热窗口”，不再用于截断历史。
            lookback_days = min(self.settings.min_required_records, 60)
            actual_start_date = self._get_date_before(self.start_date, lookback_days)
            
            # 2. 加载全量历史数据
            t_load_start = time.perf_counter()
            self.data_manager.load_historical_data(
                start_date=actual_start_date,
                end_date=self.end_date
            )
            t_load_end = time.perf_counter()
            
            # 3. 获取 K 线数据
            all_klines = self.data_manager.get_klines()
            
            if not all_klines:
                logger.warning(f"没有K线数据: stock={self.stock_id}")
                return {
                    'success': True,
                    'stock_id': self.stock_id,
                    'opportunity_count': 0,
                }
            
            # 4. 初始化追踪器（⭐ 支持多投资）
            tracker = {
                'stock_id': self.stock_id,
                'passed_dates': [],
                'active_opportunities': [],  # ⭐ 改为列表
                'all_opportunities': []      # ⭐ 所有机会（包含已完成和未完成）
            }
            
            # 5. 获取最小所需 K 线数
            min_required_kline = self.settings.min_required_records
            
            # 6. 逐日遍历 K 线
            t_enum_start = time.perf_counter()
            last_kline = None
            for i, current_kline in enumerate(all_klines):
                virtual_date_of_today = current_kline['date']
                tracker['passed_dates'].append(virtual_date_of_today)
                
                # 如果未达到最小所需K线数，跳过
                if len(tracker['passed_dates']) < min_required_kline:
                    continue
                
                # 使用游标获取"今天及之前"的数据
                data_of_today = self.data_manager.get_data_until(virtual_date_of_today)
                
                # ⭐ 执行单日枚举（多投资）
                self._enumerate_single_day(tracker, current_kline, data_of_today)
                
                last_kline = current_kline
            t_enum_end = time.perf_counter()
            
            # 7. 回测结束，强制平仓所有未结投资
            if tracker['active_opportunities'] and last_kline:
                self._close_all_open_opportunities(tracker, last_kline)
            
            # 8. 序列化并写出本股票的 CSV，再返回精简 summary
            t_serialize_start = time.perf_counter()
            opportunities_dict = [opp.to_dict() for opp in tracker['all_opportunities']]

            opportunity_count = len(opportunities_dict)
            # 如果 payload 中有 output_dir，则将当前股票的结果写入对应目录
            output_dir = self.job_payload.get('output_dir')
            if output_dir and opportunity_count > 0:
                self._save_stock_results(output_dir, opportunities_dict)
            t_serialize_end = time.perf_counter()

            t_end = time.perf_counter()

            logger.info(
                "⏱ 枚举性能[stock=%s]: load=%.1fms, enum=%.1fms, serialize+save=%.1fms, total=%.1fms, days=%d, opps=%d",
                self.stock_id,
                (t_load_end - t_load_start) * 1000.0,
                (t_enum_end - t_enum_start) * 1000.0,
                (t_serialize_end - t_serialize_start) * 1000.0,
                (t_end - t_start) * 1000.0,
                len(all_klines),
                opportunity_count,
            )

            return {
                'success': True,
                'stock_id': self.stock_id,
                'opportunity_count': opportunity_count,
            }
        
        except Exception as e:
            logger.error(
                f"枚举失败: stock_id={self.stock_id}, error={e}",
                exc_info=True
            )
            return {
                'success': False,
                'stock_id': self.stock_id,
                'opportunity_count': 0,
                'error': str(e)
            }
    
    def _enumerate_single_day(
        self,
        tracker: Dict[str, Any],
        current_kline: Dict[str, Any],
        data_of_today: Dict[str, Any]
    ):
        """
        枚举单日（⭐ 核心逻辑）
        
        流程：
        1. 检查所有 active opportunities 是否完成
        2. 扫描新机会（不管是否有持仓）
        
        Args:
            tracker: 追踪器
            current_kline: 当天的 K 线
            data_of_today: 今天及之前的所有数据
        """
        # 1. 检查所有 active opportunities
        completed_indices = []
        for idx, opportunity in enumerate(tracker['active_opportunities']):
            # ⭐ 使用 Opportunity 实例方法
            is_completed = opportunity.check_targets(
                current_kline=current_kline,
                goal_config=self.settings.goal
            )
            
            if is_completed:
                # 标记为已完成
                completed_indices.append(idx)
                
                logger.debug(
                    f"机会完成: stock={self.stock_id}, "
                    f"id={opportunity.opportunity_id}, "
                    f"date={current_kline['date']}, "
                    f"reason={opportunity.sell_reason}"
                )
        
        # 移除已完成的 opportunities（从后往前删除，避免索引错乱）
        for idx in reversed(completed_indices):
            tracker['active_opportunities'].pop(idx)
        
        # 2. 扫描新机会（⭐ 不管是否有持仓）
        opportunity = self._scan_opportunity_with_data(data_of_today)
        
        if opportunity:
            # 确保 stock 信息完整（使用 Worker 预加载的 stock_info）
            if opportunity.stock:
                opportunity.stock = {**self.stock_info, **opportunity.stock}
            else:
                opportunity.stock = self.stock_info
            
            # 框架自动填充字段（opportunity_id、strategy_name 等）
            opportunity.enrich_from_framework(
                strategy_name=self.strategy_name,
                strategy_version='1.0'  # TODO: 从 settings 获取
            )
            opportunity.status = 'active'
            opportunity.completed_targets = []
            
            # 加入追踪列表
            tracker['active_opportunities'].append(opportunity)
            tracker['all_opportunities'].append(opportunity)
            
            logger.debug(
                f"发现机会: stock={self.stock_id}, "
                f"id={opportunity.opportunity_id}, "
                f"date={opportunity.trigger_date}, "
                f"price={opportunity.trigger_price}"
            )
    
    def _scan_opportunity_with_data(self, data: Dict[str, Any]):
        """
        调用用户策略的 scan_opportunity 方法
        
        Args:
            data: 今天及之前的所有数据（包含 klines、required_entities 等）
        
        Returns:
            Opportunity or None
        """
        # 直接调用用户实现的扫描方法，传入数据字典和配置
        # 避免临时设置 data_manager._current_data，防止 IO 操作
        settings_dict = self.settings.to_dict() if hasattr(self.settings, 'to_dict') else self.settings
        return self.strategy_instance.scan_opportunity(data, settings_dict)
    
    def _close_all_open_opportunities(self, tracker: Dict[str, Any], last_kline: Dict[str, Any]):
        """
        回测结束时强制平仓所有未结投资
        
        Args:
            tracker: 追踪器
            last_kline: 最后一个交易日的 K 线
        """
        for opportunity in tracker['active_opportunities']:
            # ⭐ 使用 Opportunity 实例方法
            opportunity.settle(
                last_kline=last_kline,
                reason='enumeration_end'
            )
            
            logger.debug(
                f"强制平仓: stock={self.stock_id}, "
                f"id={opportunity.opportunity_id}, "
                f"date={last_kline['date']}"
            )
        
        # 清空 active list（所有都已完成）
        tracker['active_opportunities'].clear()
    
    def _save_stock_results(self, output_dir: str, opportunities: List[Dict[str, Any]]):
        """
        将当前股票的机会和 completed_targets 写入单独的 CSV 文件：
        - {stock_id}_opportunities.csv
        - {stock_id}_targets.csv
        """
        from pathlib import Path
        import csv
        import json

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        opp_rows: List[Dict[str, Any]] = []
        target_rows: List[Dict[str, Any]] = []

        # 定义不需要输出到 CSV 的字段（内部追踪字段、元数据字段、原始数据字段、重复信息、空值字段）
        excluded_fields = {
            "completed_targets",  # 已单独输出到 targets CSV
            "config_hash",         # 策略配置 hash（版本控制用，CSV 不需要）
            "created_at",          # 创建时间（元数据，CSV 不需要）
            "updated_at",          # 更新时间（元数据，CSV 不需要）
            "record_of_today",     # 原始 K 线记录（已有 trigger_date/trigger_price，CSV 不需要）
            "dynamic_loss_active", # 动态止损激活状态（内部追踪，CSV 不需要）
            "dynamic_loss_highest", # 动态止损最高点（内部追踪，CSV 不需要）
            "expired_reason",      # 失效原因（如果机会过期，但当前设计不使用此字段）
            "expired_date",        # 失效日期（当前设计不使用，总是为空）
            "exit_reason",         # 退出原因（在 targets CSV 中已有 reason 字段，重复）
            "protect_loss_active", # 保本止损激活状态（内部追踪，CSV 不需要）
            "opportunity_id",      # 机会ID（元数据，文件名已表明股票，可通过 trigger_date+trigger_price 唯一标识）
            "scan_date",           # 扫描日期（元数据，CSV 不需要）
            "stock",               # 股票完整信息（已有 stock_id 和 stock_name，重复）
            "stock_id",            # 股票代码（文件名已表明，CSV 不需要）
            "stock_name",          # 股票名称（文件名已表明，CSV 不需要）
            "strategy_name",       # 策略名称（目录结构已表明，CSV 不需要）
            "strategy_version",    # 策略版本（元数据，CSV 不需要）
            "holding_days",        # 持有天数（当前实现中总是为空）
            "max_drawdown",        # 最大回撤（当前实现中总是为空）
            "metadata",            # 元数据（总是空字典）
            "price_return",        # 价格收益率（在 targets CSV 中已有 roi 字段，重复）
            "tracking",            # 持有期间追踪数据（当前实现中总是为空）
            "triggered_stop_loss_idx",    # 已触发的止损阶段索引（内部追踪状态，CSV 不需要）
            "triggered_take_profit_idx",  # 已触发的止盈阶段索引（内部追踪状态，CSV 不需要）
        }

        for opp in opportunities:
            # 主表数据（排除不需要的字段）
            row = {k: v for k, v in opp.items() if k not in excluded_fields}

            # 兼容旧字段名：sell_* -> exit_*
            if "sell_date" in row and "exit_date" not in row:
                row["exit_date"] = row.pop("sell_date")
            if "sell_price" in row and "exit_price" not in row:
                row["exit_price"] = row.pop("sell_price")
            if "sell_reason" in row and "exit_reason" not in row:
                row["exit_reason"] = row.pop("sell_reason")

            # price_return 和 roi 都已排除（在 targets CSV 中已有 roi 字段）

            # extra_fields 如果是 dict，则序列化为 JSON 字符串
            if "extra_fields" in row and isinstance(row["extra_fields"], dict):
                try:
                    row["extra_fields"] = json.dumps(row["extra_fields"], ensure_ascii=False)
                except Exception:
                    row["extra_fields"] = str(row["extra_fields"])

            opp_rows.append(row)

            # 子表数据（不再包含 opportunity_id，因为 opportunities CSV 中已移除）
            # 如果需要关联，可以通过 trigger_date + trigger_price 唯一标识
            for target in opp.get("completed_targets", []) or []:
                t_row = dict(target)  # 直接使用 target 的字段，不添加 opportunity_id
                if "extra_fields" in t_row and isinstance(t_row["extra_fields"], dict):
                    try:
                        t_row["extra_fields"] = json.dumps(t_row["extra_fields"], ensure_ascii=False)
                    except Exception:
                        t_row["extra_fields"] = str(t_row["extra_fields"])
                target_rows.append(t_row)

        # 写 opportunities CSV
        if opp_rows:
            opp_file = output_path / f"{self.stock_id}_opportunities.csv"
            fieldnames = sorted({k for row in opp_rows for k in row.keys()})
            with opp_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in opp_rows:
                    writer.writerow(row)

        # 写 targets CSV
        if target_rows:
            target_file = output_path / f"{self.stock_id}_targets.csv"
            fieldnames = sorted({k for row in target_rows for k in row.keys()})
            with target_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in target_rows:
                    writer.writerow(row)
    
    def _get_date_before(self, date_str: str, days: int) -> str:
        """
        获取指定日期之前的日期
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            days: 天数
        
        Returns:
            更早的日期字符串（YYYYMMDD）
        """
        from datetime import datetime, timedelta
        
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            earlier_date = date - timedelta(days=days)
            return earlier_date.strftime('%Y%m%d')
        except Exception as e:
            logger.warning(f"计算日期失败: {e}")
            return date_str
