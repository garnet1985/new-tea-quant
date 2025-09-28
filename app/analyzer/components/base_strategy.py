#!/usr/bin/env python3
"""
策略基类 - 定义所有策略的通用接口和基础功能
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from utils.db.db_manager import DatabaseManager
from utils.icon.icon_service import IconService
from app.analyzer.components.investment.investment_recorder import InvestmentRecorder


class BaseStrategy(ABC):
    """策略基类 - 所有策略必须继承此类"""
    
    def __init__(self, db: DatabaseManager = None, is_verbose: bool = False, name: str = None, description: str = None, abbreviation: str = None):
        """
        初始化策略基类
        
        Args:
            db_manager: 已初始化的数据库管理器实例
            strategy_name: 策略名称
            strategy_prefix: 策略前缀（用于表名）
        """
        self.db = db
        self.is_verbose = is_verbose

        self.name = name
        self.description = description
        self.abbreviation = abbreviation
        
        # 策略所需的表模型
        self.table: Dict[str, Any] = {}
        
        self.investment_recorder = InvestmentRecorder()
        # 初始化策略
        self._check_required_fields()

        # scan white list, config this when during test specific stocks purpose
        # self.scan_ids = [
        #     "603198.SH",
        #     "600720.SH",
        #     "002832.SZ",
        #     "002557.SZ"
        # ]
        self.scan_ids = []

        # scan range, config this when during quick test scan_opportunity function purpose
        self.scan_range = {
            "start": 0, 
            "amount": 1
        }


    # ========================================================
    # init:
    # ========================================================

    def initialize(self):
        """初始化策略 - 自动检测和注册表，返回统一的tables字典"""
        try:
            # 自动检测和注册策略特有的表
            self._register_strategy_tables()
            
            # 创建所有注册的表
            self.db.create_registered_tables()
            
            # 返回统一的tables字典
            self.table = self._get_required_tables()
            
        except Exception as e:
            logger.error(f"{IconService.get('error')} 策略 {self.name} initialize() 失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _check_required_fields(self):
        """检查策略所需的必要字段"""
        if self.name is None:
            raise ValueError("strategy require a name.")

        if self.abbreviation is None:
            raise ValueError("strategy require a abbreviation. abbreviation is used to identify the strategy, it should be unique and machine readable.")

        if self.is_verbose:
            logger.info(f"🔧 初始化策略: {self.name}")
    

    def _register_strategy_tables(self):
        """自动检测tables文件夹并注册策略特有的表"""
        import os
        import importlib
        
        # 构建tables文件夹路径 - 使用绝对路径
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        tables_dir = os.path.join(current_file_dir, '..', 'strategy', self.abbreviation, 'tables')
        tables_dir = os.path.abspath(tables_dir)
        
        if self.is_verbose:
            logger.info(f"{IconService.get('search')} 检查策略 {self.name} 的tables文件夹: {tables_dir}")
        
        if not os.path.exists(tables_dir):
            if self.is_verbose:
                logger.info(f"策略 {self.name} 没有tables文件夹，跳过自定义表注册")
            return
        
        # 扫描tables文件夹下的所有子文件夹
        for table_name in os.listdir(tables_dir):
            table_path = os.path.join(tables_dir, table_name)
            if not os.path.isdir(table_path):
                continue
            
            # 检查是否有model.py文件
            model_file = os.path.join(table_path, 'model.py')
            if not os.path.exists(model_file):
                continue
            
            try:
                # 动态导入表模型
                module_name = f"app.analyzer.strategy.{self.abbreviation}.tables.{table_name}.model"
                table_module = importlib.import_module(module_name)
                
                # 获取模型类（通常是模块中唯一的类）
                model_class = None
                for attr_name in dir(table_module):
                    attr = getattr(table_module, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__bases__') and 
                        any('BaseTableModel' in str(base) for base in attr.__bases__)):
                        model_class = attr
                        break
                
                if model_class:
                    # 只注册表信息，不立即创建表实例
                    # 这样可以避免在错误的上下文中调用load_schema()
                    schema_path = os.path.join(table_path, 'schema.json')
                    
                    # 读取schema文件
                    import json
                    try:
                        with open(schema_path, 'r', encoding='utf-8') as f:
                            schema = json.load(f)
                    except Exception as e:
                        logger.error(f"❌ 策略 {self.name} 读取schema文件失败 {schema_path}: {e}")
                        continue
                    
                    # 注册表到数据库管理器
                    self.db.register_table(
                        table_name=table_name,
                        prefix=self.abbreviation,
                        schema=schema,
                        model_class=model_class
                    )
                    
                    if self.is_verbose:
                        logger.info(f"{IconService.get('success')} 策略 {self.name} 自动注册表: {table_name}")
                        
            except Exception as e:
                logger.error(f"{IconService.get('error')} 策略 {self.name} 注册表 {table_name} 失败: {e}")
                import traceback
                traceback.print_exc()
    
    def _get_required_tables(self):
        """构建统一的tables字典，包含基础表和自定义表"""
        # 直接构建基础表
        tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
        }
        
        # 添加自定义表（从数据库管理器的tables中获取已创建的表实例）
        # 使用list()创建副本，避免在迭代时修改字典
        for full_table_name, table_info in list(self.db.registered_tables.items()):
            # 检查是否是当前策略的表（通过表名前缀判断）
            if full_table_name.startswith(f"{self.abbreviation}_"):
                # 这是策略的自定义表
                # 从schema中获取原始表名
                schema = table_info.get('schema', {})
                original_table_name = schema.get('name', full_table_name.replace(f"{self.abbreviation}_", ""))
                
                # 直接使用已创建的表实例，而不是重新创建
                if full_table_name in self.db.tables:
                    table_instance = self.db.tables[full_table_name]
                    tables[original_table_name] = table_instance
                    
                    if self.is_verbose:
                        logger.info(f"✅ 策略 {self.name} 添加表到tables字典: {original_table_name}")
                else:
                    if self.is_verbose:
                        logger.warning(f"⚠️ 策略 {self.name} 表 {full_table_name} 未在db.tables中找到")
        
        return tables


    def set_scan_ids(self, ids: List[str]):
        """
        设置扫描的ID集合
        """
        self.scan_ids = ids

    def clear_scan_ids(self):
        """
        清空扫描的ID集合
        """
        self.scan_ids = []
    
    def clear_scan_range(self):
        """
        清空扫描的索引范围
        """
        self.scan_range = {
            "start": 0, 
            "amount": 0
        }

    def set_scan_range(self, amount, start = 0):
        """
        设置扫描的索引范围
        """
        self.scan_range['start'] = start
        self.scan_range['amount'] = amount

    # ================================================================
    # Core 1 - identify opportunity: should be override by subclass:
    # ================================================================

    # this method should be override by subclass - to define the opportunity identification logic
    @abstractmethod
    def scan_opportunity(self, stock_id: str, data: List[Dict[str, Any]], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描单只股票的投资机会 - 抽象方法，子类必须实现
        
        Args:
            stock_id: 股票ID
            data: 股票的历史K线数据（到当前日期为止）
            
        Returns:
            Optional[Dict]: 如果发现投资机会则返回机会字典，否则返回None
        """
        pass
    
    @staticmethod
    def should_settle_investment(stock_info: Dict[str, Any], record_of_today: Dict[str, Any], investment: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any]) -> bool:
        """
        判断是否应该结算投资 - 可选重写
        """
        return False


    # this method is used to scan today's opportunities for all the stocks by using multi-process
    # this is a public API method to Analyzer module
    def scan(self) -> List[Dict[str, Any]]:
        """
        扫描所有股票的投资机会 - 框架方法，内部使用多进程
        用户不需要复写此方法，只需要实现 scan_opportunity 方法
            
        Returns:
            List[Dict]: 所有发现的投资机会列表
        """

        import importlib
        strategy_setting_path = f"app.analyzer.strategy.{self.get_abbr()}.settings"
        settings_module = importlib.import_module(strategy_setting_path)
        
        strategy_settings = getattr(settings_module, "settings")
        
        stock_list = self.table["stock_index"].load_filtered_index()

        # 根据 settings 的 mode 配置确定扫描范围
        mode_config = strategy_settings.get('mode', {})
        
        # 优先级1: 如果开启 blacklist_only，扫描黑名单股票
        if mode_config.get('blacklist_only', False):
            blacklist = strategy_settings.get('goal', {}).get('blacklist', {}).get('list', [])
            if blacklist:
                stock_list = self.filter_list_by_ids(stock_list, blacklist)
                logger.info(f"📋 使用黑名单模式，扫描 {len(stock_list)} 只股票")
            else:
                logger.warning("⚠️ 启用了黑名单模式但黑名单为空，将使用其他模式")
        
        # 优先级2: 使用 scan_stock_pool 指定的股票列表
        elif mode_config.get('scan_stock_pool'):
            scan_pool = mode_config.get('scan_stock_pool', [])
            if scan_pool:
                stock_list = self.filter_list_by_ids(stock_list, scan_pool)
                logger.info(f"🎯 使用股票池模式，扫描 {len(stock_list)} 只股票")
        
        # 优先级3: 使用 start_idx 和 test_amount 进行范围测试
        elif mode_config.get('test_amount', 0) > 0:
            start_idx = mode_config.get('start_idx', 0)
            test_amount = mode_config.get('test_amount', 0)
            stock_list = stock_list[start_idx:start_idx + test_amount]
            logger.info(f"🔢 使用范围测试模式，从索引 {start_idx} 开始扫描 {len(stock_list)} 只股票")
        
        # 优先级4: 扫描全部股票
        else:
            logger.info(f"🌐 使用全量扫描模式，扫描 {len(stock_list)} 只股票")

        if not stock_list:
            logger.info(f"{IconService.get('error')} 未找到可扫描的股票")
            return []

        jobs = self._build_scan_jobs(stock_list, strategy_settings)

        opportunities = self._execute_scan_jobs(jobs)

        self.report(opportunities)
        
        return opportunities

    def filter_list_by_ids(self, stock_list: List[Dict[str, Any]], stock_ids: List[str]) -> List[Dict[str, Any]]:
        """
        扫描指定ID的股票的投资机会
        """
        new_list = []
        for stock in stock_list:
            if stock.get('id') in stock_ids:
                new_list.append(stock)
        return new_list


    def filter_list_by_range(self, stock_list: List[Dict[str, Any]], scan_range: Any) -> List[Dict[str, Any]]:
        """
        扫描指定ID的股票的投资机会
        """
        start = scan_range.get('start', 0)
        amount = scan_range.get('amount', 10)
        new_list = stock_list[start:start+amount]
        return new_list


    def _build_scan_jobs(self, stock_list: List[Dict[str, Any]], strategy_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        构建扫描任务
        """
        jobs: List[Dict[str, Any]] = []
        module_info = self.get_module_info()

        for stock in stock_list:
            jobs.append({
                'id': f"{self.get_abbr()}_{stock.get('id')}",
                'payload': {
                    'stock': stock,
                    'settings': strategy_settings.copy(),
                    'module_info': module_info,
                }
            })
        return jobs


    def _execute_scan_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行扫描任务
        """
        from utils.worker.multi_process.process_worker import ProcessWorker

        # 使用静态执行函数，避免pickle绑定到实例
        worker = ProcessWorker(
            job_executor=BaseStrategy._scan_multiprocess_executor, 
            start_method="spawn", 
            is_verbose=False
        )

        worker.run_jobs(jobs)
        # 提取成功且有结果的机会
        successful = worker.get_successful_results()
        return [r.result for r in successful if r.result]


    # multiprocess executor for scan_opportunity - must be static method otherwise it will be pickle error
    @staticmethod
    def _scan_multiprocess_executor(job: Dict[str, Any]) -> Dict[str, Any]:
        """子进程执行扫描：避免引用实例属性以绕过pickle问题"""
        stock = job.get('stock', {}) or {}
        stock_id = stock.get('id')
        settings = job.get('settings', {}) or {}
        module_info = job.get('module_info', {}) or {}

        # 子进程内直接使用 DataLoader 的静态方法，避免初始化 DatabaseManager
        from app.analyzer.components.data_loader import DataLoader
        data = DataLoader.prepare_data(stock, settings)

        # 传入setting中配置的参数并且调用子类中的scan_opportunity方法
        import importlib
        try:
            strategy_module = importlib.import_module(module_info.get('strategy_module_path', ''))
            strategy_class = getattr(strategy_module, module_info.get('strategy_class_name', ''))
        except Exception:
            raise Exception(f"❌ 策略 {module_info.get('strategy_class_name', '')} 导入失败! strategy_module_path: {module_info.get('strategy_module_path', '')} strategy_class_name: {module_info.get('strategy_class_name', '')}")

        # 直接调用静态方法，避免实例化导致的表注册/DB依赖
        opportunity = strategy_class.scan_opportunity(stock, data, settings)
        if opportunity:
            logger.info(f"{IconService.get('success')} 股票 {stock['name']} ({stock_id}) 扫描完成, 发现投资机会")
        else:
            logger.info(f"{IconService.get('error')} 股票 {stock['name']} ({stock_id}) 扫描完成, 没有投资机会")
        return opportunity


    # this method is used to convert the opportunity to a standard opportunity entity
    @staticmethod
    def to_opportunity(
        stock: Dict[str, Any],
        record_of_today: Dict[str, Any],
        extra_fields: Optional[Dict[str, Any]] = None,
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Construct a standard opportunity entity.

        Required fields: stock{id[,name?]}, record_of_today
        Optional fields: lower_bound, upper_bound, and extra (strategy-specific)
        """
        opportunity: Dict[str, Any] = {
            'stock': stock or {},
            'date': record_of_today.get('date'),
            'price': record_of_today.get('close'),
        }
        if lower_bound is not None:
            opportunity['lower_bound'] = lower_bound
        if upper_bound is not None:
            opportunity['upper_bound'] = upper_bound

        opportunity['extra_fields'] = extra_fields

        return opportunity





    # ================================================================
    # Core 2 - simulate strategy: should be override by subclass:
    # ================================================================


    # this method is used to scan today's opportunities for all the stocks by using multi-process
    # this is a public API method to Analyzer module
    def simulate(self) -> Dict[str, Any]:
        """
        模拟策略 - 使用历史数据模拟策略
        用户不需要复写此方法，只需要实现 simulate_one_day 方法
        
        Returns:
            Dict[str, Any]: 模拟结果
        """
        from .simulator.simulator import Simulator

        simulator = Simulator()

        # 运行模拟 - 传入所有回调方法
        result = simulator.run(
            module_info=self.get_module_info()
        )
        
        return result

    # Below methods are the event API to modify the simulate data structure and process, it all has a simple default implementation
    @staticmethod
    def on_before_simulate(stock_list: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        用来修改股票列表 - 可选重写

        Args:
            settings: 验证后的策略设置
            stock_list: 股票列表
        """
        return stock_list

    @staticmethod
    def on_summarize_stock_investment(base_investment_summary: Dict[str, Any], original_investment: Dict[str, Any], stock_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        单只股票投资机会汇总 - 抽象方法，子类必须实现
        """
        return base_investment_summary


    @staticmethod
    def to_investment(base_investment: Dict[str, Any]) -> Dict[str, Any]:
        """
        将投资机会转换为投资
        """
        return base_investment

    @staticmethod
    def to_settled_investment(base_investment: Dict[str, Any]) -> Dict[str, Any]:
        """
        将投资转换为已结算投资
        """
        return base_investment


    # ========================================================
    # abstract API for opportunity scanning:
    # ========================================================

    @staticmethod
    def report(opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描/模拟结果 - 可选重写
        
        Args:
            opportunities: 扫描阶段的投资机会列表（scan 使用）
            stock_summaries: 模拟阶段的按股票汇总（simulate 使用，可选）
        """
        for opportunity in opportunities:
            logger.info(f"="*80)
            logger.info(f"股票 {opportunity['stock']['name']} ({opportunity['stock']['id']})")
            logger.info(f"="*80)
            logger.info(f"扫描日期: {opportunity['date']}")
            logger.info(f"当前价格: {opportunity['price']}")
            logger.info(f"机会价格区间: {round(opportunity['lower_bound'], 2)} - {round(opportunity['upper_bound'], 2)}")
            logger.info(f"当前价格在区间位置: {AnalyzerService.to_percent(opportunity['price'] - opportunity['lower_bound'], (opportunity['upper_bound'] - opportunity['lower_bound']))}%")
        return None

    @staticmethod
    def on_summarize_stock(base_summary: Dict[str, Any], simulate_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        单只股票模拟结果汇总 - 可选重写
        
        Args:
            base_summary: 默认的汇总结果
            simulate_result: 单只股票的模拟结果
            
        Returns:
            Dict: 追加到默认summary的track（可以返回空字典）
        """
        return base_summary

    @staticmethod
    def on_summarize_session(base_session_summary: Dict[str, Any], stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        整个会话汇总 - 可选重写
        
        Args:
            base_session_summary: 默认的汇总结果
            stock_summaries: 所有股票的汇总结果
            
        Returns:
            Dict: 追加到默认session summary的字段（可以返回空字典）
        """
        return base_session_summary
    
    @staticmethod
    def on_before_report(base_report: Dict[str, Any]) -> None:
        """
        模拟完成后的最终回调 - 可选重写
        
        Args:
            base_report: 最终报告
        """
        return base_report

    # ========================================================
    # base analysis to simulation result:
    # ========================================================

    # 时间段	市场类型	主要特征/背景
    # 2008.01 ~ 2008.10	熊市	金融危机，指数暴跌
    # 2008.11 ~ 2009.07	牛市	四万亿刺激，市场反弹
    # 2009.08 ~ 2014.06	震荡市	经济回落，政策不明朗，宽幅震荡
    # 2014.07 ~ 2015.06	牛市	改革预期，杠杆资金，快速上涨
    # 2015.07 ~ 2019.01	熊市	杠杆去化，监管加强，持续回落
    # 2019.02 ~ 2021.02	牛市	科技创新，外资流入，结构性牛市
    # 2021.03 ~ 2022.10	震荡市	板块分化，指数横盘
    # 2022.11 ~ 2023.04	牛市	疫后修复，资金推动，反弹
    # 2023.05 ~ 2024.01	熊市	经济压力，市场信心不足
    # 2024.02 ~ 2025.09	震荡市	政策托底，市场反复

    # 市场周期定义
    MARKET_PERIODS = [
        ("20080101", "20081031", "bear"),      # 熊市：金融危机
        ("20081101", "20090731", "bull"),      # 牛市：四万亿刺激
        ("20090801", "20140630", "stable"),    # 震荡市：经济回落
        ("20140701", "20150630", "bull"),      # 牛市：改革预期
        ("20150701", "20190131", "bear"),      # 熊市：杠杆去化
        ("20190201", "20210228", "bull"),      # 牛市：科技创新
        ("20210301", "20221031", "stable"),    # 震荡市：板块分化
        ("20221101", "20230430", "bull"),      # 牛市：疫后修复
        ("20230501", "20240131", "bear"),      # 熊市：经济压力
        ("20240201", "20250930", "stable"),    # 震荡市：政策托底
    ]

    def _get_market_type(self, date_str: str) -> str:
        """根据日期获取市场类型"""
        date_num = int(date_str[:8])  # YYYYMMDD
        
        for start_date, end_date, market_type in self.MARKET_PERIODS:
            start_num = int(start_date)
            end_num = int(end_date)
            if start_num <= date_num <= end_num:
                return market_type
        
        return "unknown"

    def _parse_date_for_grouping(self, date_str: str) -> tuple:
        """解析日期用于分组"""
        if len(date_str) >= 8:
            year = date_str[:4]
            month = date_str[4:6]
            return year, month
        return None, None

    def _group_by_time_period(self, data_list: List[Dict[str, Any]], date_field: str) -> Dict[str, Any]:
        """按时间段分组数据"""
        by_year = {}
        by_month = {}
        
        for item in data_list:
            date_str = item.get(date_field, "")
            if not date_str:
                continue
                
            year, month = self._parse_date_for_grouping(date_str)
            if not year or not month:
                continue
            
            year_key = year
            month_key = f"{year}-{month}"
            
            if year_key not in by_year:
                by_year[year_key] = []
            by_year[year_key].append(item)
            
            if month_key not in by_month:
                by_month[month_key] = []
            by_month[month_key].append(item)
        
        return {
            'by_year': by_year,
            'by_month': by_month
        }

    def get_opportunity_distribution(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取投资机会分布
        
        Args:
            opportunities: 投资机会列表
            
        Returns:
            Dict[str, Any]: 按年份和月份分组的投资机会分布
        """
        return self._group_by_time_period(opportunities, 'date')

    def get_performance_in_every_period(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取每个时期的投资表现
        
        Args:
            investments: 投资记录列表
            
        Returns:
            Dict[str, Any]: 按年份和月份分组的投资表现
        """
        return self._group_by_time_period(investments, 'invest_date')

    def get_successful_investment_distribution(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取成功投资分布
        
        Args:
            investments: 投资记录列表
            
        Returns:
            Dict[str, Any]: 按年份和月份分组的成功投资分布
        """
        # 过滤成功投资（假设有roi字段，>0为成功）
        successful_investments = [
            inv for inv in investments 
            if inv.get('roi', 0) > 0
        ]
        return self._group_by_time_period(successful_investments, 'invest_date')

    def get_failed_investment_distribution(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取失败投资分布
        
        Args:
            investments: 投资记录列表
            
        Returns:
            Dict[str, Any]: 按年份和月份分组的失败投资分布
        """
        # 过滤失败投资（假设有roi字段，<=0为失败）
        failed_investments = [
            inv for inv in investments 
            if inv.get('roi', 0) <= 0
        ]
        return self._group_by_time_period(failed_investments, 'invest_date')

    def _get_performance_by_market_type(self, investments: List[Dict[str, Any]], market_type: str) -> Dict[str, Any]:
        """根据市场类型获取投资表现"""
        filtered_investments = []
        
        for inv in investments:
            invest_date = inv.get('invest_date', '')
            if invest_date and self._get_market_type(invest_date) == market_type:
                filtered_investments.append(inv)
        
        if not filtered_investments:
            return {
                'total_investments': 0,
                'successful_investments': 0,
                'failed_investments': 0,
                'win_rate': 0.0,
                'avg_roi': 0.0,
                'total_roi': 0.0,
                'investments': []
            }
        
        # 计算统计信息
        total_investments = len(filtered_investments)
        successful_investments = len([inv for inv in filtered_investments if inv.get('roi', 0) > 0])
        failed_investments = total_investments - successful_investments
        win_rate = (successful_investments / total_investments * 100) if total_investments > 0 else 0.0
        total_roi = sum(inv.get('roi', 0) for inv in filtered_investments)
        avg_roi = total_roi / total_investments if total_investments > 0 else 0.0
        
        return {
            'total_investments': total_investments,
            'successful_investments': successful_investments,
            'failed_investments': failed_investments,
            'win_rate': win_rate,
            'avg_roi': avg_roi,
            'total_roi': total_roi,
            'investments': filtered_investments
        }

    def get_strategy_performance_in_uptrend_market(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取策略在牛市的表现
        
        Args:
            investments: 投资记录列表
            
        Returns:
            Dict[str, Any]: 牛市中的投资表现统计
        """
        return self._get_performance_by_market_type(investments, 'bull')

    def get_strategy_performance_in_downtrend_market(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取策略在熊市的表现
        
        Args:
            investments: 投资记录列表
            
        Returns:
            Dict[str, Any]: 熊市中的投资表现统计
        """
        return self._get_performance_by_market_type(investments, 'bear')

    def get_strategy_performance_in_stable_market(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取策略在震荡市的表现
        
        Args:
            investments: 投资记录列表
            
        Returns:
            Dict[str, Any]: 震荡市中的投资表现统计
        """
        return self._get_performance_by_market_type(investments, 'stable')

    def _extract_investments_from_simulation_results(self, simulation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从模拟结果中提取投资记录（适配多种数据结构）
        
        Args:
            simulation_results: 模拟结果数据
            
        Returns:
            List[Dict[str, Any]]: 投资记录列表
        """
        investments = []
        stocks = simulation_results.get('stocks', [])
        
        for stock_data in stocks:
            # 适配不同的数据结构：HL策略使用'stock'，其他策略可能使用'stock_info'
            stock_id = stock_data.get('stock', {}).get('id', '') or stock_data.get('stock_info', {}).get('id', '')
            summary = stock_data.get('summary', {})
            
            # 从汇总中提取投资信息
            total_investments = summary.get('total_investments', 0)
            avg_roi = summary.get('avg_roi', 0)
            
            # 如果有具体的投资记录，使用实际记录
            if 'investments' in stock_data:
                for inv in stock_data['investments']:
                    # 适配HL策略的字段：start_date/end_date, overall_profit_rate, duration_in_days
                    investment_record = {
                        'stock_id': stock_id,
                        'invest_date': inv.get('start_date', '') or inv.get('invest_date', ''),
                        'sell_date': inv.get('end_date', '') or inv.get('sell_date', ''),
                        'roi': inv.get('overall_profit_rate', 0) * 100 if inv.get('overall_profit_rate') is not None else inv.get('roi', 0),  # 转换为百分比
                        'duration_days': inv.get('duration_in_days', 0) or inv.get('duration_days', 0),
                    }
                    investments.append(investment_record)
            else:
                # 如果没有具体记录，创建汇总记录
                if total_investments > 0:
                    investment_record = {
                        'stock_id': stock_id,
                        'invest_date': 'unknown',  # 如果没有具体日期
                        'sell_date': 'unknown',
                        'roi': avg_roi,
                        'duration_days': summary.get('avg_duration_days', 0),
                    }
                    investments.append(investment_record)
        
        return investments

    def _extract_opportunities_from_simulation_results(self, simulation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从模拟结果中提取投资机会记录
        
        Args:
            simulation_results: 模拟结果数据
            
        Returns:
            List[Dict[str, Any]]: 投资机会列表
        """
        opportunities = []
        stocks = simulation_results.get('stocks', [])
        
        for stock_data in stocks:
            # 适配不同的数据结构：HL策略使用'stock'，其他策略可能使用'stock_info'
            stock_id = stock_data.get('stock', {}).get('id', '') or stock_data.get('stock_info', {}).get('id', '')
            
            # 如果有具体的投资记录，提取投资日期作为机会日期
            if 'investments' in stock_data:
                for inv in stock_data['investments']:
                    # 适配HL策略的字段：start_date
                    opportunity_record = {
                        'stock_id': stock_id,
                        'date': inv.get('start_date', '') or inv.get('invest_date', ''),
                        'roi': inv.get('overall_profit_rate', 0) * 100 if inv.get('overall_profit_rate') is not None else inv.get('roi', 0),
                    }
                    opportunities.append(opportunity_record)
            else:
                # 如果没有具体记录，使用汇总信息
                summary = stock_data.get('summary', {})
                total_investments = summary.get('total_investments', 0)
                if total_investments > 0:
                    opportunity_record = {
                        'stock_id': stock_id,
                        'date': 'unknown',
                        'roi': summary.get('avg_roi', 0),
                    }
                    opportunities.append(opportunity_record)
        
        return opportunities

    def analyze_simulation_results(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析模拟结果，生成完整的分析报告
        
        Args:
            simulation_results: 模拟结果数据
            
        Returns:
            Dict[str, Any]: 完整的分析报告
        """
        investments = self._extract_investments_from_simulation_results(simulation_results)
        opportunities = self._extract_opportunities_from_simulation_results(simulation_results)
        
        analysis = {
            'session_summary': simulation_results.get('session', {}),
            'opportunity_distribution': self.get_opportunity_distribution(opportunities),
            'performance_in_every_period': self.get_performance_in_every_period(investments),
            'successful_investment_distribution': self.get_successful_investment_distribution(investments),
            'failed_investment_distribution': self.get_failed_investment_distribution(investments),
            'bull_market_performance': self.get_strategy_performance_in_uptrend_market(investments),
            'bear_market_performance': self.get_strategy_performance_in_downtrend_market(investments),
            'stable_market_performance': self.get_strategy_performance_in_stable_market(investments),
        }
        
        return analysis

    def get_base_analysis(self, strategy_folder_name: str = "HL", session_id: str = None) -> Dict[str, Any]:
        """
        获取基础分析报告
        
        Args:
            strategy_folder_name: 策略文件夹名称，默认为"HL"
            session_id: 会话ID，如果为None则使用最新的会话ID
            
        Returns:
            Dict[str, Any]: 完整的分析报告
        """
        try:
            # 设置投资记录器的策略文件夹
            self.investment_recorder.set_strategy_folder_name(strategy_folder_name)
            
            # 获取模拟结果
            simulation_results = self.investment_recorder.get_simulation_results(session_id)
            
            if not simulation_results.get('session') or not simulation_results.get('stocks'):
                logger.warning(f"策略 {strategy_folder_name} 没有找到模拟结果数据")
                return {
                    'error': 'No simulation data found',
                    'strategy': strategy_folder_name,
                    'session_id': session_id
                }
            
            # 分析模拟结果
            analysis = self.analyze_simulation_results(simulation_results)
            
            # 添加策略信息
            analysis['strategy_info'] = {
                'strategy_name': strategy_folder_name,
                'session_id': session_id or self.investment_recorder.get_latest_session_id(),
                'analysis_time': datetime.now().isoformat(),
                'total_stocks': len(simulation_results.get('stocks', [])),
            }
            
            logger.info(f"✅ 成功生成策略 {strategy_folder_name} 的基础分析报告")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 生成策略 {strategy_folder_name} 基础分析报告失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'error': str(e),
                'strategy': strategy_folder_name,
                'session_id': session_id
            }

    def analysis(self, session_id: str = None) -> Dict[str, Any]:
        """
        策略分析接口 - 自动调用基础分析并打印结果
        
        Args:
            session_id: 会话ID，如果为None则使用最新的会话ID
            
        Returns:
            Dict[str, Any]: 完整的分析报告
        """
        logger.info(f"🔍 开始分析策略 {self.name} 的模拟结果")
        
        # 调用基础分析，使用abbreviation作为策略文件夹名称
        analysis_result = self.get_base_analysis(self.abbreviation, session_id)
        
        if 'error' in analysis_result:
            logger.error(f"❌ 策略分析失败: {analysis_result['error']}")
            return analysis_result
        
        # 打印分析结果
        self._print_analysis_results(analysis_result)
        
        return analysis_result

    def _print_analysis_results(self, analysis: Dict[str, Any]) -> None:
        """
        打印分析结果
        
        Args:
            analysis: 分析结果字典
        """
        print(f"\n{'='*60}")
        print(f"📊 策略分析报告")
        print(f"{'='*60}")
        
        # 策略信息
        strategy_info = analysis.get('strategy_info', {})
        print(f"策略名称: {strategy_info.get('strategy_name', 'Unknown')}")
        print(f"会话ID: {strategy_info.get('session_id', 'Unknown')}")
        print(f"分析时间: {strategy_info.get('analysis_time', 'Unknown')}")
        print(f"股票数量: {strategy_info.get('total_stocks', 0)}")
        
        # 会话汇总
        session = analysis.get('session_summary', {})
        print(f"\n📈 整体表现:")
        print(f"  总投资次数: {session.get('total_investments', 0)}")
        print(f"  当前投资次数: {session.get('total_open_investments', 0)}")
        print(f"  总股票数: {session.get('stocks_have_opportunities', 0)}")
        print(f"  有投资的股票数: {session.get('stocks_have_opportunities', 0)}")
        print(f"  胜率: {session.get('win_rate', 0):.1f}%")
        
        # 统一ROI格式：session summary中的avg_roi是小数形式，转换为百分比
        avg_roi = session.get('avg_roi', 0)
        avg_roi_percent = avg_roi * 100  # 转换为百分比
        print(f"  平均ROI: {avg_roi_percent:.2f}%")
        
        # 年化收益：session summary中的annual_return已经是百分比形式
        annual_return = session.get('annual_return', 0)
        print(f"  平均年化收益: {annual_return:.2f}%")
        print(f"  平均持有时长: {session.get('avg_duration_in_days', 0):.0f}天")
        
        # 各市场表现
        bull_perf = analysis['bull_market_performance']
        bear_perf = analysis['bear_market_performance']
        stable_perf = analysis['stable_market_performance']
        
        print(f"\n🎯 各市场表现:")
        print(f"  🐂 牛市: 投资{bull_perf['total_investments']}次, 胜率{bull_perf['win_rate']:.1f}%, 平均ROI {bull_perf['avg_roi']:.2f}%")
        print(f"  🐻 熊市: 投资{bear_perf['total_investments']}次, 胜率{bear_perf['win_rate']:.1f}%, 平均ROI {bear_perf['avg_roi']:.2f}%")
        print(f"  📈 震荡市: 投资{stable_perf['total_investments']}次, 胜率{stable_perf['win_rate']:.1f}%, 平均ROI {stable_perf['avg_roi']:.2f}%")
        
        # 投资分布分析（合并显示）
        opp_dist = analysis['opportunity_distribution']
        perf_dist = analysis['performance_in_every_period']
        success_dist = analysis['successful_investment_distribution']
        failed_dist = analysis['failed_investment_distribution']
        
        print(f"\n📅 投资分布分析:")
        
        # 按年份合并显示
        print(f"  按年份分布:")
        if opp_dist['by_year']:
            # 计算总数
            total_opportunities = sum(len(opps) for opps in opp_dist['by_year'].values())
            total_investments = sum(len(invs) for invs in perf_dist['by_year'].values())
            total_success = sum(len(invs) for invs in success_dist['by_year'].values())
            total_failed = sum(len(invs) for invs in failed_dist['by_year'].values())
            
            # 显示所有年份
            for year in sorted(opp_dist['by_year'].keys()):
                # 机会数据
                opps = opp_dist['by_year'].get(year, [])
                opp_count = len(opps)
                opp_percentage = (opp_count / total_opportunities * 100) if total_opportunities > 0 else 0
                
                # 投资表现数据
                invs = perf_dist['by_year'].get(year, [])
                inv_count = len(invs)
                avg_roi = sum(inv.get('roi', 0) for inv in invs) / len(invs) if invs else 0
                
                # 成功投资数据
                success_invs = success_dist['by_year'].get(year, [])
                success_count = len(success_invs)
                success_percentage = (success_count / total_success * 100) if total_success > 0 else 0
                success_rate_in_year = (success_count / inv_count * 100) if inv_count > 0 else 0
                
                # 失败投资数据
                failed_invs = failed_dist['by_year'].get(year, [])
                failed_count = len(failed_invs)
                failed_percentage = (failed_count / total_failed * 100) if total_failed > 0 else 0
                failed_rate_in_year = (failed_count / inv_count * 100) if inv_count > 0 else 0
                
                print(f"\n    {year}年: {opp_count}个机会 (总占比{opp_percentage:.1f}%) - 平均ROI {avg_roi:.2f}% 其中:")
                print(f"      - {IconService.get('success')}成功投资: {success_count}次 占比{success_rate_in_year:.1f}% | (总占比{success_percentage:.1f}%)")
                print(f"      - {IconService.get('failed')}失败投资: {failed_count}次 占比{failed_rate_in_year:.1f}% | (总占比{failed_percentage:.1f}%)")
        
        # 按月份合并显示
        print(f"\n  按月份分布 (1-12月):")
        if opp_dist['by_month']:
            # 统计月份数据
            month_opp_stats = {}
            month_success_stats = {}
            month_failed_stats = {}
            month_roi_stats = {}  # 添加ROI统计
            
            # 机会月份统计
            for month_key, opps in opp_dist['by_month'].items():
                if '-' in month_key:
                    month = month_key.split('-')[1]
                    if month not in month_opp_stats:
                        month_opp_stats[month] = 0
                    month_opp_stats[month] += len(opps)
            
            # 成功投资月份统计
            for month_key, invs in success_dist['by_month'].items():
                if '-' in month_key:
                    month = month_key.split('-')[1]
                    if month not in month_success_stats:
                        month_success_stats[month] = 0
                    month_success_stats[month] += len(invs)
            
            # 失败投资月份统计
            for month_key, invs in failed_dist['by_month'].items():
                if '-' in month_key:
                    month = month_key.split('-')[1]
                    if month not in month_failed_stats:
                        month_failed_stats[month] = 0
                    month_failed_stats[month] += len(invs)
            
            # 计算月份平均ROI
            for month_key, invs in perf_dist['by_month'].items():
                if '-' in month_key:
                    month = month_key.split('-')[1]
                    if month not in month_roi_stats:
                        month_roi_stats[month] = []
                    month_roi_stats[month].extend(invs)
            
            # 计算总数
            total_month_opp = sum(month_opp_stats.values())
            total_month_success = sum(month_success_stats.values())
            total_month_failed = sum(month_failed_stats.values())
            
            # 显示1-12月分布
            for month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                opp_count = month_opp_stats.get(month, 0)
                opp_percentage = (opp_count / total_month_opp * 100) if total_month_opp > 0 else 0
                
                success_count = month_success_stats.get(month, 0)
                success_percentage = (success_count / total_month_success * 100) if total_month_success > 0 else 0
                
                failed_count = month_failed_stats.get(month, 0)
                failed_percentage = (failed_count / total_month_failed * 100) if total_month_failed > 0 else 0
                
                # 计算该月份内的成功/失败率
                month_total_inv = success_count + failed_count
                success_rate_in_month = (success_count / month_total_inv * 100) if month_total_inv > 0 else 0
                failed_rate_in_month = (failed_count / month_total_inv * 100) if month_total_inv > 0 else 0
                
                # 计算该月份平均ROI
                month_invs = month_roi_stats.get(month, [])
                avg_roi = sum(inv.get('roi', 0) for inv in month_invs) / len(month_invs) if month_invs else 0
                
                print(f"\n    {month}月: {opp_count}个机会 (总占比{opp_percentage:.1f}%) - 平均ROI {avg_roi:.2f}% 其中:")
                print(f"      - {IconService.get('success')} 成功投资: {success_count}次 占比{success_rate_in_month:.1f}% | (总占比{success_percentage:.1f}%)")
                print(f"      - {IconService.get('failed')} 失败投资: {failed_count}次 占比{failed_rate_in_month:.1f}% | (总占比{failed_percentage:.1f}%)")
        
        print(f"\n{'='*60}")
        print(f"✅ 策略分析完成")
        print(f"{'='*60}")




    # ========================================================
    # utils:
    # ========================================================
    
    def get_abbr(self) -> str:
        """获取策略的缩写"""
        return self.abbreviation

    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        abbreviation = self.get_abbr()
        return {
            'strategy_class_name': self.__class__.__name__,
            'strategy_folder_name': abbreviation,
            'strategy_module_path': f"app.analyzer.strategy.{abbreviation}.{abbreviation}",
            'strategy_settings_path': f"app.analyzer.strategy.{abbreviation}.settings"
        }

