#!/usr/bin/env python3
"""
策略基类 - 定义所有策略的通用接口和基础功能
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from loguru import logger
from utils.db.db_manager import DatabaseManager
from .settings_validator import SettingsValidator


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

    def _check_required_fields(self):
        """检查策略所需的必要字段"""
        if self.name is None:
            raise ValueError("strategy require a name.")

        if self.abbreviation is None:
            raise ValueError("strategy require a abbreviation. abbreviation is used to identify the strategy, it should be unique and machine readable.")

        if self.is_verbose:
            logger.info(f"🔧 初始化策略: {self.name}")
    
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
            logger.error(f"❌ 策略 {self.name} initialize() 失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _register_strategy_tables(self):
        """自动检测tables文件夹并注册策略特有的表"""
        import os
        import importlib
        
        # 构建tables文件夹路径 - 使用绝对路径
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        tables_dir = os.path.join(current_file_dir, '..', 'strategy', self.abbreviation, 'tables')
        tables_dir = os.path.abspath(tables_dir)
        
        if self.is_verbose:
            logger.info(f"🔍 检查策略 {self.name} 的tables文件夹: {tables_dir}")
        
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
                        logger.info(f"✅ 策略 {self.name} 自动注册表: {table_name}")
                        
            except Exception as e:
                logger.error(f"❌ 策略 {self.name} 注册表 {table_name} 失败: {e}")
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
    
    def get_abbr(self) -> str:
        """获取策略的缩写"""
        return self.abbreviation
    
    @staticmethod
    def validate_and_merge_settings(settings: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
        """校验并合并默认值，返回可用配置；无副作用，不写入实例。"""
        validator = SettingsValidator()
        is_valid, errors = validator.validate_settings(settings, strategy_name)
        if not is_valid:
            details = "\n".join([f"  - {e}" for e in errors])
            raise ValueError(f"策略 {strategy_name} 设置验证失败:\n{details}")
        return validator.merge_with_defaults(settings)



    # ========================================================
    # Scan jobs:
    # ========================================================
    
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

        # TODO: 测试用，删除
        stock_list = stock_list[:2]

        if not stock_list:
            logger.info("❌ 未找到可扫描的股票")
            return []

        jobs = self._build_scan_jobs(stock_list, strategy_settings)

        opportunities = self._execute_scan_jobs(jobs)

        self.report(opportunities)
        
        return opportunities

    def _build_scan_jobs(self, stock_list: List[Dict[str, Any]], strategy_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        构建扫描任务
        """
        jobs: List[Dict[str, Any]] = []
        strategy_class_name = self.__class__.__name__
        strategy_module_path = f"app.analyzer.strategy.{self.get_abbr()}.{self.get_abbr()}"

        for stock in stock_list:
            jobs.append({
                'id': f"{self.get_abbr()}_{stock.get('id')}",
                'payload': {
                    'stock': stock,
                    'settings': strategy_settings.copy(),
                    'strategy_class_name': strategy_class_name,
                    'strategy_module_path': strategy_module_path,
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


    @staticmethod
    def _scan_multiprocess_executor(job: Dict[str, Any]) -> Dict[str, Any]:
        """子进程执行扫描：避免引用实例属性以绕过pickle问题"""
        stock = job.get('stock', {}) or {}
        stock_id = stock.get('id')
        settings = job.get('settings', {}) or {}
        strategy_class_name = job.get('strategy_class_name', '')
        strategy_module_path = job.get('strategy_module_path', '')

        data = {}

        # 子进程内直接使用 DataLoader 的静态方法，避免初始化 DatabaseManager
        from app.analyzer.components.data_loader import DataLoader
        data['klines'] = DataLoader.load_stock_data_in_child_process(stock_id, settings)

        # 传入setting中配置的参数并且调用子类中的scan_opportunity方法
        import importlib
        try:
            strategy_module = importlib.import_module(strategy_module_path)
            strategy_class = getattr(strategy_module, strategy_class_name)
        except Exception:
            raise Exception(f"❌ 策略 {strategy_class_name} 导入失败! strategy_module_path: {strategy_module_path} strategy_class_name: {strategy_class_name}")

        strategy_instance = strategy_class(db=None)

        return strategy_instance.scan_opportunity(stock, data, settings)


    
    def simulate(self) -> Dict[str, Any]:
        """
        模拟策略 - 使用历史数据模拟策略
        用户不需要复写此方法，只需要实现 simulate_one_day 方法
        
        Returns:
            Dict[str, Any]: 模拟结果
        """
        from .simulator.simulator import Simulator
        
        simulator = Simulator()
        
        # 运行模拟 - 使用用户定义的 simulate_one_day 方法
        result = simulator.run(
            settings=self.settings.copy(),
            on_simulate_one_day=self.simulate_one_day,
            on_single_stock_summary=self.stock_summary,
            on_simulate_complete=None
        )
        
        return result
    
    @abstractmethod
    def simulate_one_day(self, stock_id: str, current_date: str, current_record: Dict[str, Any], 
                        historical_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        模拟单日交易逻辑 - 抽象方法，子类必须实现
        
        Args:
            stock_id: 股票ID
            current_date: 当前日期
            current_record: 当前日K线数据
            historical_data: 历史数据（到当前日之前）
            current_investment: 当前投资状态
            
        Returns:
            Dict[str, Any]: 包含以下字段的结果
                - new_investment: 新的投资（如果有）
                - settled_investments: 结算的投资列表
                - current_investment: 更新后的当前投资状态
        """
        pass
    
    @abstractmethod
    def stock_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        单只股票模拟结果汇总 - 抽象方法，子类必须实现
        
        Args:
            result: 单只股票的模拟结果（包含 investments/settled_investments）
            
        Returns:
            Dict: 追加到默认summary的track（可以返回空字典）
        """
        pass

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
    
    @abstractmethod
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描结果 - 抽象方法，子类必须实现
        
        Args:
            opportunities: 投资机会列表
        """
        pass

