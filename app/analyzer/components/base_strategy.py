#!/usr/bin/env python3
"""
策略基类 - 定义所有策略的通用接口和基础功能
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from utils.date.date_utils import DateUtils
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from utils.db.db_manager import DatabaseManager
from utils.icon.icon_service import IconService
from app.analyzer.components.investment.investment_recorder import InvestmentRecorder
from app.data_loader import DataLoader
import pandas
from app.analyzer.analyzer_service import AnalyzerService


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
        # 如果子类已经设置了version，则保持不变
        if not hasattr(self, 'version'):
            self.version = None
        
        # 策略所需的表模型
        self.table: Dict[str, Any] = {}
        
        self.investment_recorder = InvestmentRecorder()
        # 初始化策略
        self._check_required_fields()

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

        if self.version is None:
            raise ValueError("strategy require a version.")
    

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
    def should_stop_loss(stock_info: Dict[str, Any], record_of_today: Dict[str, Any], investment: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        自定义止损逻辑 - 可选重写
        
        重要约定：如果策略配置中 stop_loss.is_customized=True，
        此方法必须返回包含 'target_info' 字段的 investment 对象。
        否则将抛出 ValueError。
        
        Args:
            stock_info: 股票信息
            record_of_today: 当前交易日记录
            investment: 投资对象
            required_data: 所需数据
            settings: 策略设置
            
        Returns:
            (是否触发止损, 更新后的投资对象)
            
            如果 is_customized=True，investment 必须包含 'target_info' 字段：
            {
                'target_price': 止损目标价格,
                'current_price': 当前价格
            }
            
        Raises:
            ValueError: 如果 is_customized=True 但没有返回 target_info 字段
        """
        return False, investment
    
    @staticmethod
    def call_and_validate_strategy_method(
        strategy_class: Any,
        method_name: str,
        stock_info: Dict[str, Any], 
        record_of_today: Dict[str, Any], 
        investment: Dict[str, Any], 
        required_data: Dict[str, Any], 
        settings: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        统一的策略方法调用和校验proxy
        
        自动检查settings中是否有customized goal，如果有则验证返回的target_info
        
        Args:
            strategy_class: 策略类
            method_name: 方法名 ('should_stop_loss' 或 'should_take_profit')
            stock_info: 股票信息
            record_of_today: 当前交易日记录
            investment: 投资对象
            required_data: 所需数据
            settings: 策略设置
            
        Returns:
            (是否触发, 更新后的investment)
            
        Raises:
            ValueError: 如果is_customized=True但没有返回target_info
            AttributeError: 如果策略类没有该方法
        """
        # 调用方法
        method = getattr(strategy_class, method_name)
        is_triggered, result = method(stock_info, record_of_today, investment, required_data, settings)
        
        # 检查settings中是否有customized goal
        goal_config = settings.get('goal', {})
        
        # 检查是否为customized配置
        is_customized = False
        if method_name == 'should_stop_loss':
            is_customized = goal_config.get('stop_loss', {}).get('is_customized', False)
        elif method_name == 'should_take_profit':
            is_customized = goal_config.get('take_profit', {}).get('is_customized', False)
        
        # 如果是customized配置，必须返回target_info
        if is_customized and 'target_info' not in result:
            raise ValueError(
                f"策略 {strategy_class.__name__} 的 {method_name} 方法必须返回 'target_info' 字段，"
                "格式: return (bool, {**investment, 'target_info': {'target_price': x, 'current_price': y}})"
            )
        
        return is_triggered, result
    
    @staticmethod
    def get_next_stop_loss_target(
        stock_info: Dict[str, Any], 
        record_of_today: Dict[str, Any], 
        investment: Dict[str, Any], 
        required_data: Dict[str, Any], 
        settings: Dict[str, Any],
        strategy_class=None
    ) -> Optional[Dict[str, Any]]:
        """
        获取下一个止损目标 - 用于investment tracker
        
        这个方法会调用should_stop_loss，但只关注其返回的目标信息
        
        Args:
            stock_info: 股票信息
            record_of_today: 当前交易日记录
            investment: 投资对象（简化版，只包含holding信息）
            required_data: 所需数据
            settings: 策略设置
            strategy_class: 策略类（用于调用子类重写的方法）
            
        Returns:
            None 或 目标信息字典
        """
        # 如果提供了strategy_class，使用它调用should_stop_loss
        if strategy_class:
            is_triggered, result = strategy_class.should_stop_loss(
                stock_info, record_of_today, investment, required_data, settings
            )
        else:
            # 否则使用当前类（可能被重写）
            is_triggered, result = BaseStrategy.should_stop_loss(
                stock_info, record_of_today, investment, required_data, settings
            )
        
        # 检查investment中是否有target_info字段
        if isinstance(result, dict) and 'target_info' in result:
            return result['target_info']
        
        return None
    
    @staticmethod
    def get_stop_loss_target(
        holding: Dict[str, Any], 
        current_price: float, 
        settings: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        计算止损目标价格 - 可选重写
        
        这个方法用于investment tracker，不需要复杂的investment对象
        只需要基本的持仓信息就可以计算出目标价格
        
        Args:
            holding: 当前持仓信息 {amount, avg_cost, ...}
            current_price: 当前价格
            settings: 策略设置
            
        Returns:
            None 或 {name, type, ratio, target_price, target_amount}
            - name: 目标名称
            - type: 'stop_loss'
            - ratio: 目标收益率（负数）
            - target_price: 目标价格
            - target_amount: 需要卖出的数量（None表示全部）
        """
        return None
    
    @staticmethod
    def get_take_profit_target(
        holding: Dict[str, Any], 
        current_price: float, 
        settings: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        计算止盈目标价格 - 可选重写
        
        这个方法用于investment tracker，不需要复杂的investment对象
        
        Args:
            holding: 当前持仓信息 {amount, avg_cost, ...}
            current_price: 当前价格
            settings: 策略设置
            
        Returns:
            None 或 {name, type, ratio, target_price, sell_ratio, target_amount}
            - name: 目标名称
            - type: 'take_profit'
            - ratio: 目标收益率（正数）
            - target_price: 目标价格
            - sell_ratio: 需要卖出的比例（0.0-1.0）
            - target_amount: 需要卖出的数量
        """
        return None

    @staticmethod
    def should_take_profit(stock_info: Dict[str, Any], record_of_today: Dict[str, Any], investment: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        自定义止盈逻辑 - 可选重写
        
        重要约定：如果策略配置中 take_profit.is_customized=True，
        此方法必须返回包含 'target_info' 字段的 investment 对象。
        否则将抛出 ValueError。
        
        Args:
            stock_info: 股票信息
            record_of_today: 当前交易日记录
            investment: 投资对象
            required_data: 所需数据
            settings: 策略设置
            
        Returns:
            (是否触发止盈, 更新后的投资对象)
            
            如果 is_customized=True，investment 必须包含 'target_info' 字段：
            {
                'target_price': 止盈目标价格,
                'current_price': 当前价格
            }
            
        Raises:
            ValueError: 如果 is_customized=True 但没有返回 target_info 字段
        """
        return False, investment
    
    @staticmethod
    def get_next_take_profit_target(
        stock_info: Dict[str, Any], 
        record_of_today: Dict[str, Any], 
        investment: Dict[str, Any], 
        required_data: Dict[str, Any], 
        settings: Dict[str, Any],
        strategy_class=None
    ) -> Optional[Dict[str, Any]]:
        """
        获取下一个止盈目标 - 用于investment tracker
        
        这个方法会调用should_take_profit，但只关注其返回的目标信息
        
        Args:
            stock_info: 股票信息
            record_of_today: 当前交易日记录
            investment: 投资对象（简化版，只包含holding信息）
            required_data: 所需数据
            settings: 策略设置
            strategy_class: 策略类（用于调用子类重写的方法）
            
        Returns:
            None 或 目标信息字典
        """
        # 如果提供了strategy_class，使用它调用should_take_profit
        if strategy_class:
            is_triggered, result = strategy_class.should_take_profit(
                stock_info, record_of_today, investment, required_data, settings
            )
        else:
            # 否则使用当前类（可能被重写）
            is_triggered, result = BaseStrategy.should_take_profit(
                stock_info, record_of_today, investment, required_data, settings
            )
        
        # 检查investment中是否有next_target字段
        if isinstance(result, dict) and 'next_target' in result:
            return result['next_target']
        
        return None


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
        
        # 使用 DataLoader 加载股票列表（使用过滤规则，排除ST、科创板等）
        loader = DataLoader(self.db)
        stock_list = loader.load_stock_list(filtered=True)

        # 使用AnalyzerService的统一采样方法
        stock_list = AnalyzerService.sample_stock_list(stock_list, strategy_settings)

        if not stock_list:
            logger.info(f"{IconService.get('error')} 未找到可扫描的股票")
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

        # 子进程内直接使用 DataLoader，避免初始化 DatabaseManager
        from app.data_loader import DataLoader
        loader = DataLoader()  # 子进程内自行创建DatabaseManager
        data = loader.prepare_data(stock, settings)

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
        
        If lower_bound/upper_bound are not provided, defaults to ±1% of price
        """
        current_price = record_of_today.get('close', 0)
        
        opportunity: Dict[str, Any] = {
            'stock': stock or {},
            'date': record_of_today.get('date'),
            'price': current_price,
        }
        
        # 如果未提供边界，使用默认值（±1%）
        if lower_bound is None:
            lower_bound = current_price * 0.99
        if upper_bound is None:
            upper_bound = current_price * 1.01
        
        opportunity['lower_bound'] = lower_bound
        opportunity['upper_bound'] = upper_bound

        if extra_fields is not None:
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
        将投资机会转换为投资 - 可选重写, 用来改变base_investment的字段
        """
        return base_investment

    @staticmethod
    def to_alt_settled_investment(base_investment: Dict[str, Any]) -> Dict[str, Any]:
        """
        将投资转换为已结算投资 - 可选重写, 用来改变base_investment的字段
        """
        return base_investment

    @staticmethod
    def to_settled_investment(
        investment: Dict[str, Any],
        exit_price: float,
        exit_date: str,
        sell_ratio: float = 1.0,
        target_type: str = "customized_goal"
    ) -> Dict[str, Any]:
        """
        结算投资 - 简化API
        
        Args:
            investment: 投资对象
            exit_price: 退出价格
            exit_date: 退出日期 (YYYYMMDD格式)
            sell_ratio: 卖出比例 (0.0-1.0)，默认1.0表示全仓
            target_type: 目标类型，默认"customized_goal"
            
        Returns:
            更新后的投资对象
        """
        # 获取购买信息
        purchase_price = investment['purchase_price']
        purchase_date = investment['start_date']
        
        # 计算收益率
        profit_ratio = (exit_price - purchase_price) / purchase_price
        profit = exit_price - purchase_price
        
        # 创建完成目标
        completed_target = {
            'type': target_type,
            'ratio': profit_ratio,
            'sell_ratio': sell_ratio,
            'profit': profit,
            'exit_price': exit_price,
            'exit_date': exit_date,
            'purchase_price': purchase_price,
            'purchase_date': purchase_date,
            'is_achieved': True,
        }
        
        # 更新投资对象
        if 'targets' not in investment:
            investment['targets'] = {}
        
        investment['targets']['completed'] = [completed_target]
        investment['targets']['investment_ratio_left'] = 1.0 - sell_ratio
        investment['end_date'] = exit_date
        
        return investment



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
            
            # lower_bound 和 upper_bound 是可选的
            if 'lower_bound' in opportunity and 'upper_bound' in opportunity:
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
    def on_summarize_session(base_session_summary: Dict[str, Any], stock_summaries: List[Dict[str, Any]], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        整个会话汇总 - 可选重写
        
        Args:
            base_session_summary: 默认的汇总结果
            stock_summaries: 所有股票的汇总结果
            settings: 策略设置（可选）
            
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
    
    @staticmethod
    def present_extra_session_report(session_summary: Dict[str, Any], settings: Dict[str, Any] = None) -> None:
        """
        展示自定义 session 报告 - 可选重写
        
        在 present_session_report 输出标准报告后，额外输出自定义内容
        
        Args:
            session_summary: session汇总结果
            settings: 策略设置（可选）
        """
        pass  # 默认不输出任何内容

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
                'analysis_time': DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD_HH_MM_SS),
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
    # support testing strategy:
    # ========================================================


    def mark_period(self, records: List[Dict], condition_func: callable, min_period_length: int = 1, return_format: str = "dict") -> List[Dict]:
        """
        标记满足条件的K线区间
        
        Args:
            records: K线数据记录列表，按时间顺序排列
            condition_func: 判断条件函数，接收一个record参数，返回True/False
            min_period_length: 最小区间长度，默认为1
            return_format: 返回格式，"dict"或"dataframe"，默认为"dict"
            
        Returns:
            List[Dict] 或 pandas.DataFrame: 标记的区间列表，每个区间包含:
                - start_date: 开始日期
                - end_date: 结束日期
                - start_idx: 开始索引
                - end_idx: 结束索引
                - duration: 持续时间（天数）
                - records: 区间内的所有记录
                
        注意: 基础区间信息只包含上述字段，如需详细统计信息，请使用独立的工具方法：
            - get_price_statistics_from_period()
            - get_volume_statistics_from_period()
            - get_ma_statistics_from_period()
            - get_extreme_prices_from_period()
        
        Example:
            # 标记MA5 > MA10 > MA20 > MA60的区间
            def ma_condition(record):
                return (record.get('ma5', 0) > record.get('ma10', 0) and 
                        record.get('ma10', 0) > record.get('ma20', 0) and 
                        record.get('ma20', 0) > record.get('ma60', 0))
            
            # 返回字典格式
            periods = strategy.mark_period(records, ma_condition, min_period_length=5)
            
            # 返回DataFrame格式
            periods_df = strategy.mark_period(records, ma_condition, min_period_length=5, return_format="dataframe")
        """
        if not records or not condition_func:
            return [] if return_format == "dict" else None
        
        periods = []
        current_period = []
        in_period = False
        
        for idx, record in enumerate(records):
            meets_condition = condition_func(record)
            
            if meets_condition:
                if not in_period:
                    # 开始新的区间
                    in_period = True
                    current_period = [record]
                else:
                    # 继续当前区间
                    current_period.append(record)
            else:
                if in_period:
                    # 结束当前区间
                    if len(current_period) >= min_period_length:
                        period_info = self._create_simple_period_info(current_period, records)
                        periods.append(period_info)
                    current_period = []
                    in_period = False
        
        # 处理最后一个区间（如果记录以满足条件结束）
        if in_period and len(current_period) >= min_period_length:
            period_info = self._create_simple_period_info(current_period, records)
            periods.append(period_info)
        
        # 根据格式返回结果
        if return_format == "dataframe":
            return self._periods_to_dataframe(periods)
        else:
            return periods
    
    def _create_simple_period_info(self, period_records: List[Dict], all_records: List[Dict]) -> Dict:
        """
        创建简单的区间信息字典（只包含基本信息）
        
        Args:
            period_records: 区间内的记录
            all_records: 所有记录（用于计算索引）
            
        Returns:
            Dict: 简单的区间信息
        """
        start_record = period_records[0]
        end_record = period_records[-1]
        
        # 计算索引
        start_idx = all_records.index(start_record)
        end_idx = all_records.index(end_record)
        
        return {
            'start_date': start_record.get('date', ''),
            'end_date': end_record.get('date', ''),
            'start_idx': start_idx,
            'end_idx': end_idx,
            'duration': len(period_records),
            'records': period_records,
        }
    
    def mark_convergence_periods(self, records: List[Dict], convergence_threshold: float = 0.08, min_period_length: int = 3) -> List[Dict]:
        """
        标记均线收敛区间（专门用于RTB策略）
        
        Args:
            records: K线数据记录列表
            convergence_threshold: 收敛阈值，默认为0.08
            min_period_length: 最小区间长度，默认为3
            
        Returns:
            List[Dict]: 收敛区间列表
        """
        def convergence_condition(record):
            # 计算均线收敛度
            ma5 = record.get('ma5', 0)
            ma10 = record.get('ma10', 0)
            ma20 = record.get('ma20', 0)
            ma60 = record.get('ma60', 0)
            close = record.get('close', 0)
            
            if not all([ma5, ma10, ma20, ma60, close]):
                return False
            
            ma_values = [ma5, ma10, ma20, ma60]
            ma_max = max(ma_values)
            ma_min = min(ma_values)
            ma_convergence = (ma_max - ma_min) / close
            
            return ma_convergence < convergence_threshold
        
        return self.mark_period(records, convergence_condition, min_period_length)
    
    def mark_ma_trend_periods(self, records: List[Dict], trend_type: str = "bull", min_period_length: int = 5) -> List[Dict]:
        """
        标记均线趋势区间
        
        Args:
            records: K线数据记录列表
            trend_type: 趋势类型，"bull"(多头)或"bear"(空头)
            min_period_length: 最小区间长度，默认为5
            
        Returns:
            List[Dict]: 趋势区间列表
        """
        if trend_type == "bull":
            def bull_condition(record):
                # 多头排列：MA5 > MA10 > MA20 > MA60
                return (record.get('ma5', 0) > record.get('ma10', 0) and 
                        record.get('ma10', 0) > record.get('ma20', 0) and 
                        record.get('ma20', 0) > record.get('ma60', 0))
            condition_func = bull_condition
        elif trend_type == "bear":
            def bear_condition(record):
                # 空头排列：MA5 < MA10 < MA20 < MA60
                return (record.get('ma5', 0) < record.get('ma10', 0) and 
                        record.get('ma10', 0) < record.get('ma20', 0) and 
                        record.get('ma20', 0) < record.get('ma60', 0))
            condition_func = bear_condition
        else:
            raise ValueError("trend_type must be 'bull' or 'bear'")
        
        return self.mark_period(records, condition_func, min_period_length)
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """
        计算序列的波动性（标准差）
        
        Args:
            values: 数值列表
            
        Returns:
            float: 标准差
        """
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """
        计算趋势强度（价格变化的一致性）
        
        Args:
            prices: 价格列表
            
        Returns:
            float: 趋势强度，-1到1之间，1表示强烈上涨趋势，-1表示强烈下跌趋势
        """
        if len(prices) < 2:
            return 0
        
        # 计算价格变化方向的一致性
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        positive_changes = sum(1 for change in changes if change > 0)
        negative_changes = sum(1 for change in changes if change < 0)
        
        total_changes = len(changes)
        if total_changes == 0:
            return 0
        
        # 计算趋势强度
        trend_ratio = (positive_changes - negative_changes) / total_changes
        return trend_ratio
    
    def _calculate_max_drawdown(self, prices: List[float]) -> float:
        """
        计算最大回撤
        
        Args:
            prices: 价格列表
            
        Returns:
            float: 最大回撤值
        """
        if len(prices) < 2:
            return 0
        
        max_drawdown = 0
        peak = prices[0]
        
        for price in prices:
            if price > peak:
                peak = price
            drawdown = peak - price
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _periods_to_dataframe(self, periods: List[Dict]) -> 'pandas.DataFrame':
        """
        将区间列表转换为DataFrame格式
        
        Args:
            periods: 区间列表
            
        Returns:
            pandas.DataFrame: 区间数据的DataFrame
        """
        try:
            import pandas as pd
            
            if not periods:
                return pd.DataFrame()
            
            # 准备DataFrame数据，排除records字段（太复杂）
            df_data = []
            for period in periods:
                row = {k: v for k, v in period.items() if k != 'records'}
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # 设置日期索引
            if 'start_date' in df.columns:
                df['start_date'] = pd.to_datetime(df['start_date'], format='%Y%m%d', errors='coerce')
            if 'end_date' in df.columns:
                df['end_date'] = pd.to_datetime(df['end_date'], format='%Y%m%d', errors='coerce')
            
            return df
            
        except ImportError:
            logger.warning("pandas not available, returning list instead")
            return periods
    
    def analyze_periods(self, periods: List[Dict]) -> Dict:
        """
        分析区间列表的整体特征
        
        Args:
            periods: 区间列表
            
        Returns:
            Dict: 分析结果，包含各种统计指标
        """
        if not periods:
            return {}
        
        # 提取各种指标
        durations = [p.get('duration', 0) for p in periods]
        price_changes = [p.get('price_change_pct', 0) for p in periods]
        volatilities = [p.get('price_volatility', 0) for p in periods]
        max_drawdowns = [p.get('max_drawdown_pct', 0) for p in periods]
        
        # 计算统计指标
        analysis = {
            'total_periods': len(periods),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            
            'avg_price_change': sum(price_changes) / len(price_changes) if price_changes else 0,
            'max_price_change': max(price_changes) if price_changes else 0,
            'min_price_change': min(price_changes) if price_changes else 0,
            'positive_periods': sum(1 for pc in price_changes if pc > 0),
            'negative_periods': sum(1 for pc in price_changes if pc < 0),
            'win_rate': sum(1 for pc in price_changes if pc > 0) / len(price_changes) if price_changes else 0,
            
            'avg_volatility': sum(volatilities) / len(volatilities) if volatilities else 0,
            'max_volatility': max(volatilities) if volatilities else 0,
            'min_volatility': min(volatilities) if volatilities else 0,
            
            'avg_max_drawdown': sum(max_drawdowns) / len(max_drawdowns) if max_drawdowns else 0,
            'max_drawdown': max(max_drawdowns) if max_drawdowns else 0,
            'min_drawdown': min(max_drawdowns) if max_drawdowns else 0,
        }
        
        return analysis
    
    def find_best_periods(self, periods: List[Dict], criteria: str = "price_change_pct", top_n: int = 5) -> List[Dict]:
        """
        找出最佳的区间
        
        Args:
            periods: 区间列表
            criteria: 排序标准，可选值：price_change_pct, duration, max_drawdown_pct等
            top_n: 返回前N个
            
        Returns:
            List[Dict]: 排序后的最佳区间列表
        """
        if not periods:
            return []
        
        # 根据标准排序
        if criteria in ['max_drawdown_pct', 'price_volatility', 'volume_volatility']:
            # 对于这些指标，越小越好
            sorted_periods = sorted(periods, key=lambda x: x.get(criteria, float('inf')))
        else:
            # 对于其他指标，越大越好
            sorted_periods = sorted(periods, key=lambda x: x.get(criteria, float('-inf')), reverse=True)
        
        return sorted_periods[:top_n]
    
    # ========================================================
    # Period Analysis Tools (可选的统计方法)
    # ========================================================
    
    def get_price_statistics_from_period(self, period: Dict) -> Dict:
        """
        从单个period中提取价格统计信息
        
        Args:
            period: 区间字典，必须包含'records'字段
            
        Returns:
            Dict: 价格统计信息
        """
        records = period.get('records', [])
        if not records:
            return {}
        
        prices = [record.get('close', 0) for record in records if record.get('close')]
        if not prices:
            return {}
        
        highs = [record.get('highest', 0) for record in records if record.get('highest')]
        lows = [record.get('lowest', 0) for record in records if record.get('lowest')]
        
        start_price = prices[0]
        end_price = prices[-1]
        max_price = max(highs) if highs else max(prices)
        min_price = min(lows) if lows else min(prices)
        
        return {
            'start_price': start_price,
            'end_price': end_price,
            'max_price': max_price,
            'min_price': min_price,
            'avg_price': sum(prices) / len(prices),
            'price_change': end_price - start_price,
            'price_change_pct': ((end_price - start_price) / start_price * 100) if start_price > 0 else 0,
            'price_range': max_price - min_price,
            'price_range_pct': ((max_price - min_price) / start_price * 100) if start_price > 0 else 0,
        }
    
    def get_volume_statistics_from_period(self, period: Dict) -> Dict:
        """
        从单个period中提取成交量统计信息
        
        Args:
            period: 区间字典，必须包含'records'字段
            
        Returns:
            Dict: 成交量统计信息
        """
        records = period.get('records', [])
        if not records:
            return {}
        
        volumes = [record.get('volume', 0) for record in records if record.get('volume')]
        if not volumes:
            return {}
        
        return {
            'max_volume': max(volumes),
            'min_volume': min(volumes),
            'avg_volume': sum(volumes) / len(volumes),
            'volume_change': volumes[-1] - volumes[0] if len(volumes) > 1 else 0,
            'volume_change_pct': ((volumes[-1] - volumes[0]) / volumes[0] * 100) if len(volumes) > 1 and volumes[0] > 0 else 0,
        }
    
    def get_ma_statistics_from_period(self, period: Dict) -> Dict:
        """
        从单个period中提取移动平均线统计信息
        
        Args:
            period: 区间字典，必须包含'records'字段
            
        Returns:
            Dict: MA统计信息
        """
        records = period.get('records', [])
        if not records:
            return {}
        
        start_record = records[0]
        end_record = records[-1]
        
        return {
            'start_ma5': start_record.get('ma5', None),
            'start_ma10': start_record.get('ma10', None),
            'start_ma20': start_record.get('ma20', None),
            'start_ma60': start_record.get('ma60', None),
            'end_ma5': end_record.get('ma5', None),
            'end_ma10': end_record.get('ma10', None),
            'end_ma20': end_record.get('ma20', None),
            'end_ma60': end_record.get('ma60', None),
        }
    
    def get_extreme_prices_from_period(self, period: Dict) -> Dict:
        """
        从单个period中提取极值价格信息
        
        Args:
            period: 区间字典，必须包含'records'字段
            
        Returns:
            Dict: 极值价格信息，包含极值出现的日期
        """
        records = period.get('records', [])
        if not records:
            return {}
        
        highs = [(record.get('highest', 0), record.get('date', '')) for record in records if record.get('highest')]
        lows = [(record.get('lowest', 0), record.get('date', '')) for record in records if record.get('lowest')]
        
        if not highs or not lows:
            return {}
        
        max_high = max(highs, key=lambda x: x[0])
        min_low = min(lows, key=lambda x: x[0])
        
        return {
            'max_price': max_high[0],
            'max_price_date': max_high[1],
            'min_price': min_low[0],
            'min_price_date': min_low[1],
        }




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
