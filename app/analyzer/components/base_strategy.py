#!/usr/bin/env python3
"""
策略基类 - 定义所有策略的通用接口和基础功能
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from utils.db.db_manager import DatabaseManager
from .settings_validator import SettingsValidator
from utils.icon.icon_service import IconService


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
            "amount": 5
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

        if len(self.scan_ids):
            stock_list = self.filter_list_by_ids(stock_list, self.scan_ids)
        if self.scan_range.get('amount') > 0:
            stock_list = self.filter_list_by_range(stock_list, self.scan_range)

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

        data = {}

        # 子进程内直接使用 DataLoader 的静态方法，避免初始化 DatabaseManager
        from app.analyzer.components.data_loader import DataLoader
        DataLoader.prepare_data(stock, settings)

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