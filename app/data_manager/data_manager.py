#!/usr/bin/env python3
"""
数据管理服务 - 统一的数据访问层

职责：
- 管理 DatabaseManager（唯一持有者）
- 初始化数据库和表结构
- 提供统一的数据访问 API
- 协调各个专用 Loader

架构：
- DataManager: 数据访问层入口，管理 DB 和 Loaders
- KlineLoader: K线数据专用加载器
- MacroLoader: 宏观数据专用加载器
- CorporateFinanceLoader: 企业财务专用加载器
- LabelLoader: 标签数据专用加载器
"""
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from loguru import logger
import threading

from utils.db.db_manager import DatabaseManager
from app.data_manager.loaders.macro_loader import MacroEconomyLoader
from app.data_manager.loaders.corporate_finance_loader import CorporateFinanceLoader

from .loaders import KlineLoader
from .loaders import LabelLoader
from app.conf.conf import data_default_start_date
from app.enums import KlineTerm, AdjustType
from utils.date.date_utils import DateUtils


class DataManager:
    """
    数据管理服务（数据访问总入口）

    职责：
    - 唯一持有和管理 DatabaseManager
    - 初始化数据库、连接池、表结构（Base Tables + 策略表）
    - 提供统一的数据访问 API（对应用/策略暴露的门面）
    - 协调各专用 Loader（兼容层）
    - 预留 Repository / 策略表 Model 的注册与访问能力（新架构方向）

    单例模式：
    - 单进程环境下：使用同一个实例（线程安全）
    - 多进程环境下：每个进程有独立的实例（进程间内存不共享）
    - 支持通过 force_new=True 强制创建新实例

    使用方式：
        from app.data_manager import DataManager

        # 自动使用单例（推荐）
        data_mgr = DataManager(is_verbose=True)
        data = data_mgr.prepare_data(stock, settings)
        
        # 强制创建新实例（不推荐，除非有特殊需求）
        data_mgr = DataManager(is_verbose=True, force_new=True)
    """
    
    # 单例实例（每个进程独立）
    _instance: Optional['DataManager'] = None
    _lock = threading.Lock()  # 线程安全锁
    
    @classmethod
    def reset_instance(cls):
        """
        重置单例实例（主要用于测试或特殊场景）
        
        注意：此方法会清除当前的单例实例，下次创建时会重新初始化
        """
        with cls._lock:
            cls._instance = None
    
    @classmethod
    def get_instance(cls) -> Optional['DataManager']:
        """
        获取当前的单例实例（如果存在）
        
        Returns:
            DataManager 实例，如果不存在则返回 None
        """
        return cls._instance
    
    def __new__(cls, db: Optional[DatabaseManager] = None, is_verbose: bool = False, force_new: bool = False):
        """
        单例模式实现
        
        Args:
            db: 可选的 DatabaseManager 实例
            is_verbose: 是否输出详细日志
            force_new: 是否强制创建新实例（默认 False，使用单例）
        
        Returns:
            DataManager 实例
        """
        # 如果强制创建新实例，直接创建
        if force_new:
            instance = super().__new__(cls)
            return instance
        
        # 单例模式：如果实例不存在，创建新实例
        if cls._instance is None:
            with cls._lock:
                # 双重检查，避免多线程竞争
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db: Optional[DatabaseManager] = None, is_verbose: bool = False, force_new: bool = False):
        """
        初始化数据管理器

        Args:
            db: 可选的 DatabaseManager 实例，如果提供则使用该实例，否则创建新实例
            is_verbose: 是否输出详细日志
            force_new: 是否强制创建新实例（单例模式下忽略）
        
        注意：
            - 初始化会自动调用 initialize()，无需手动调用
            - initialize() 是幂等的，多次调用只会执行一次
            - 单例模式下，如果实例已初始化，会复用现有实例的配置
        """
        # 单例模式：如果已经初始化，不重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            # 如果提供了新的参数，更新配置（但保持已初始化的状态）
            if is_verbose and not self.is_verbose:
                self.is_verbose = is_verbose
            return
        
        self.is_verbose = is_verbose
        self.db = db
        self._initialized = False

        # Loaders（延迟初始化）
        self.kline_loader = None
        self.label_loader = None
        self.macro_loader = None
        self.corporate_finance_loader = None

        # TradingDateCache（交易日缓存）
        self._trading_date_cache = None

        # DataService 容器（按名称索引，例如：'stock'、'macro'、'waly' 等）
        self._data_services: Dict[str, Any] = {}

        # 策略表 & 策略 Model 注册信息
        # {(strategy_name, table_name): schema_path}
        self._strategy_table_schemas: Dict[tuple, str] = {}
        # {(strategy_name, table_name): ModelClass}
        self._strategy_model_classes: Dict[tuple, Any] = {}
        
        # 自动初始化（幂等，多次调用只执行一次）
        self.initialize()
    
    def initialize(self):
        """
        初始化数据管理器
        
        步骤：
        1. 创建并初始化 DatabaseManager（连接池）
        2. 创建所有 Base Tables
        3. 初始化所有 Loaders
        
        注意：
            - 此方法是幂等的，多次调用只会执行一次
            - 在 __init__ 中会自动调用，通常无需手动调用
        """
        # 幂等检查：如果已经初始化，直接返回
        if self._initialized:
            return
        
        try:
            
            # 1. 初始化 DatabaseManager（只初始化连接池，不创建表）
            if self.db is None:
                if self.is_verbose:
                    logger.info("🔧 初始化 DatabaseManager...")
                self.db = DatabaseManager(is_verbose=self.is_verbose)
                self.db.initialize()
                # 设置为默认实例，便于 DbBaseModel 等自动获取 db
                DatabaseManager.set_default(self.db)
            else:
                if self.is_verbose:
                    logger.info("🔧 使用已提供的 DatabaseManager 实例...")

            # 2. 创建所有 Base Tables（业务逻辑）
            if self.is_verbose:
                logger.info("🔧 创建 Base Tables...")

            self.db.schema_manager.create_all_tables(self.db.get_connection)

            # 3. 初始化所有 Loaders
            if self.is_verbose:
                logger.info("🔧 初始化 Loaders...")
            
            self.kline_loader = KlineLoader(self.db)
            self.label_loader = LabelLoader(self.db)
            self.macro_loader = MacroEconomyLoader(self.db)
            self.corporate_finance_loader = CorporateFinanceLoader(self.db)

            # 4. 初始化 TradingDateCache
            if self.is_verbose:
                logger.info("🔧 初始化 TradingDateCache...")
            from app.data_manager.data_services.trading_date.trading_date_cache import TradingDateCache
            self._trading_date_cache = TradingDateCache()

            # 5. 初始化 DataService（按业务领域分类）
            if self.is_verbose:
                logger.info("🔧 初始化 DataService...")
            self._init_data_services()

            self._initialized = True
            
            if self.is_verbose:
                logger.info("✅ DataManager 初始化完成")
                
        except Exception as e:
            logger.error(f"❌ DataManager 初始化失败: {e}")
            raise

    # ------------------------------------------------------------------
    # Model 访问（基础表）
    # ------------------------------------------------------------------

    def get_model(self, table_name: str) -> Any:
        """
        获取指定表对应的 Model 实例
        
        返回的是个性化 Model（如 StockKlineModel），而不是 DbBaseModel
        
        Args:
            table_name: 表名，例如 'stock_kline'、'stock_list' 等
            
        Returns:
            对应的 Model 实例（已自动绑定默认 db）
            
        Example:
            kline_model = data_manager.get_model('stock_kline')
            klines = kline_model.load_by_stock_and_date_range(...)
        """
        # 表名到 Model 类的映射
        from app.data_manager.base_tables import (
            StockKlineModel, StockListModel, AdjFactorModel, AdjFactorEventModel,
            GdpModel, PriceIndexesModel, ShiborModel, LprModel,
            CorporateFinanceModel, StockLabelsModel,
            InvestmentTradesModel, InvestmentOperationsModel,
            IndustryCapitalFlowModel,
            StockIndexIndicatorModel, StockIndexIndicatorWeightModel,
            MetaInfoModel
        )
        
        model_map = {
            'stock_kline': StockKlineModel,
            'stock_list': StockListModel,
            'adj_factor': AdjFactorModel,
            'adj_factor_event': AdjFactorEventModel,
            'gdp': GdpModel,
            'price_indexes': PriceIndexesModel,
            'shibor': ShiborModel,
            'lpr': LprModel,
            'corporate_finance': CorporateFinanceModel,
            'stock_labels': StockLabelsModel,
            'investment_trades': InvestmentTradesModel,
            'investment_operations': InvestmentOperationsModel,
            'industry_capital_flow': IndustryCapitalFlowModel,
            'stock_index_indicator': StockIndexIndicatorModel,
            'stock_index_indicator_weight': StockIndexIndicatorWeightModel,
            'meta_info': MetaInfoModel,
        }
        
        model_class = model_map.get(table_name)
        if not model_class:
            logger.warning(f"表 '{table_name}' 没有对应的 Model 类")
            return None
        
        # 返回 Model 实例（自动获取默认 db）
        return model_class()

    # ------------------------------------------------------------------
    # DataService 相关
    # ------------------------------------------------------------------

    def _init_data_services(self):
        """
        初始化3大类 DataService
        
        数据分类：
        1. stock_related: 股票相关数据（K线、财务、行业）
        2. macro_system: 宏观/系统数据（GDP、CPI、Shibor、元信息）
        3. ui_transit: UI/中转数据（投资记录、扫描结果）
        
        支持两级访问：
        - 'stock_related' 访问大类统一接口
        - 'stock_related.stock' 访问子 Service
        """
        # 1. stock_related 大类
        try:
            from app.data_manager.data_services.stock_related import StockRelatedDataService
            stock_related = StockRelatedDataService(self)
            stock_related.initialize()
            
            # 注册大类
            self._data_services['stock_related'] = stock_related
            
            # 注册子 Service（支持 'stock_related.stock' 访问）
            if stock_related.stock_service:
                self._data_services['stock_related.stock'] = stock_related.stock_service
            
            if stock_related.finance_service:
                self._data_services['stock_related.corporate_finance'] = stock_related.finance_service
                # 为了向后兼容，保留简短别名
                self._data_services['corporate_finance'] = stock_related.finance_service
            
            if self.is_verbose:
                logger.info("✅ StockRelatedDataService 已注册")
        except ImportError as e:
            if self.is_verbose:
                logger.debug(f"StockRelatedDataService 未实现，跳过: {e}")
        
        # 2. macro_system 大类
        try:
            from app.data_manager.data_services.macro_system import MacroSystemDataService
            macro_system = MacroSystemDataService(self)
            macro_system.initialize()
            
            # 注册大类
            self._data_services['macro_system'] = macro_system
            
            # 注册子 Service
            if macro_system.macro_service:
                self._data_services['macro_system.macro'] = macro_system.macro_service
            
            # 为了向后兼容，保留 'macro' 这个简短别名
            self._data_services['macro'] = macro_system
            
            if self.is_verbose:
                logger.info("✅ MacroSystemDataService 已注册")
        except ImportError as e:
            if self.is_verbose:
                logger.debug(f"MacroSystemDataService 未实现，跳过: {e}")
        
        # 3. ui_transit 大类
        try:
            from app.data_manager.data_services.ui_transit import UiTransitDataService
            ui_transit = UiTransitDataService(self)
            ui_transit.initialize()
            
            # 注册大类
            self._data_services['ui_transit'] = ui_transit
            
            # 注册子 Service
            if ui_transit.investment_service:
                self._data_services['ui_transit.investment'] = ui_transit.investment_service
                # 为了向后兼容，保留简短别名
                self._data_services['investment'] = ui_transit.investment_service
            
            if self.is_verbose:
                logger.info("✅ UiTransitDataService 已注册")
        except ImportError as e:
            if self.is_verbose:
                logger.debug(f"UiTransitDataService 未实现，跳过: {e}")

    def get_data_service(self, name: str) -> Any:
        """
        获取指定名称的 DataService
        
        支持两级访问：
        - 'stock_related': 获取大类统一接口
        - 'stock_related.stock': 获取子 Service
        - 'macro': 快捷别名，等同于 'macro_system'

        Args:
            name: DataService 名称
                - 大类: 'stock_related', 'macro_system', 'ui_transit'
                - 子级: 'stock_related.stock', 'macro_system.macro'
                - 别名: 'macro' (等同于 'macro_system')

        Returns:
            对应的 DataService 实例，未找到返回 None
        """
        service = self._data_services.get(name)
        if not service:
            logger.warning(f"DataService '{name}' 未注册。可用的: {list(self._data_services.keys())}")
        return service
    
    def resolve_data_requirements(self, settings: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        配置驱动的数据获取
        
        根据策略的 data_requirements 配置，自动获取所需的数据。
        
        工作方式：
        1. 检查是否命中预设组合（大类内的优化查询）
        2. 如果没有预设，使用默认方式（分别查询）
        3. 依赖 simulator 的缓存保证性能
        
        Args:
            settings: 策略的 data_requirements 配置
                例如：{
                    'stock_kline': {...},
                    'corporate_finance': {...},
                    'macro_economy': {...}
                }
            context: 当前上下文
                例如：{
                    'ts_code': '000001.SZ',
                    'date': '20240101',
                    'quarter': '2024Q1'
                }
        
        Returns:
            数据字典，key 为配置中的数据类型，value 为对应的数据
        """
        result = {}
        processed = set()
        
        # ========== 检查预设组合 ==========
        
        # 预设1: stock_kline + corporate_finance (股票相关大类内)
        if 'stock_kline' in settings and 'corporate_finance' in settings and 'stock_kline' not in processed:
            stock_related = self.get_data_service('stock_related')
            if stock_related and 'ts_code' in context and 'date' in context and 'quarter' in context:
                try:
                    combined = stock_related.load_stock_with_finance(
                        context['ts_code'], context['date'], context['quarter']
                    )
                    result['stock_kline'] = combined['kline']
                    result['corporate_finance'] = combined['finance']
                    processed.add('stock_kline')
                    processed.add('corporate_finance')
                except Exception as e:
                    logger.debug(f"预设组合查询失败，将使用默认方式: {e}")
        
        # ========== 默认查询（没有命中预设的数据） ==========
        
        for data_type, config in settings.items():
            if data_type in processed:
                continue
            
            # 股票K线数据
            if data_type == 'stock_kline':
                stock_service = self.get_data_service('stock_related.stock')
                if stock_service and 'ts_code' in context and 'date' in context:
                    # TODO: 根据 config 参数调用对应的方法
                    result['stock_kline'] = stock_service.load_kline(
                        context['ts_code'], context['date']
                    )
            
            # 财务数据
            elif data_type == 'corporate_finance':
                finance_service = self.get_data_service('corporate_finance')
                if finance_service and 'ts_code' in context and 'quarter' in context:
                    indicators = config.get('indicators') if isinstance(config, dict) else None
                    result['corporate_finance'] = finance_service.load_financials(
                        context['ts_code'], context['quarter'], indicators
                    )
            
            # 股票标签
            elif data_type == 'stock_labels':
                stock_service = self.get_data_service('stock_related.stock')
                if stock_service and 'ts_code' in context and 'date' in context:
                    result['stock_labels'] = stock_service.load_labels(
                        context['ts_code'], context['date']
                    )
            
            # 宏观经济数据
            elif data_type == 'macro_economy':
                macro_service = self.get_data_service('macro')
                if macro_service and 'date' in context:
                    # 如果配置要求完整快照
                    if isinstance(config, dict) and config.get('full_snapshot'):
                        result['macro_economy'] = macro_service.load_macro_snapshot(context['date'])
                    # 如果指定了指标
                    elif isinstance(config, dict) and 'indicators' in config:
                        result['macro_economy'] = {}
                        for indicator in config['indicators']:
                            if indicator == 'shibor':
                                result['macro_economy']['shibor'] = macro_service.load_shibor(
                                    context['date'], context['date']
                                )
                            elif indicator == 'lpr':
                                result['macro_economy']['lpr'] = macro_service.load_lpr(
                                    context['date'], context['date']
                                )
                            # 其他指标...
                    # 默认加载快照
                    else:
                        result['macro_economy'] = macro_service.load_macro_snapshot(context['date'])
            
            # 投资记录
            elif data_type == 'investment_operations':
                investment_service = self.get_data_service('investment')
                if investment_service and 'ts_code' in context:
                    result['investment_operations'] = investment_service.load_trades_by_stock(
                        context['ts_code']
                    )
            
            # 未知数据类型，记录警告
            else:
                logger.warning(f"未识别的数据类型: {data_type}")
        
        return result

    # ------------------------------------------------------------------
    # 策略表 / 策略 Model 注册与访问（新架构预留）
    # ------------------------------------------------------------------

    def register_strategy_table(self, strategy_name: str, table_name: str, schema_path: str):
        """
        注册策略自定义表的 schema 信息

        注意：
        - 仅记录 schema 路径，真正的建表仍由 DbSchemaManager + DatabaseManager 完成
        - DataManager.initialize() 之后调用本方法，不会自动创建表
        - 后续可以提供显式的“创建策略表”入口
        """
        key = (strategy_name, table_name)
        self._strategy_table_schemas[key] = schema_path

    def register_strategy_model(self, strategy_name: str, table_name: str, model_class: Any):
        """
        注册策略表对应的 Model 类

        Args:
            strategy_name: 策略名称（例如 'Waly'）
            table_name: 表名（例如 'waly_signals'）
            model_class: 继承 DbBaseModel 的 Model 类
        """
        key = (strategy_name, table_name)
        self._strategy_model_classes[key] = model_class

    def get_strategy_model(self, strategy_name: str, table_name: str) -> Any:
        """
        获取策略表对应的 Model 实例

        - 使用 DatabaseManager 的默认实例自动注入 db
        - 如果未注册，会给出 warning 并返回 None
        """
        key = (strategy_name, table_name)
        model_class = self._strategy_model_classes.get(key)
        if not model_class:
            logger.warning(f"策略表 Model 未注册: strategy={strategy_name}, table={table_name}")
            return None

        # Model 基于 DbBaseModel，db 参数可选，内部会自动获取默认实例
        return model_class()
    
    def prepare_data(self, stock: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备所有需要的数据（聚合方法）
        
        用于策略分析，一次性加载所有需要的数据
        
        Args:
            stock: 股票信息
            settings: 数据设置（包含klines、macro、corporate_finance等配置）
            
        Returns:
            Dict: {
                'klines': {...},
                'macro': {...},
                'corporate_finance': {...},
                'labels': {...},
                ...
            }
        """
        data = {}
        stock_id = stock.get('id')
        
        # 1. 加载K线数据
        klines_settings = settings.get("klines")
        if klines_settings:
            # 将 simulation 中的 start_date 和 end_date 传递给 klines_settings
            # 创建副本避免修改原始 settings
            klines_settings_with_dates = klines_settings.copy()
            simulation_settings = settings.get("simulation", {})
            if simulation_settings.get('start_date') and 'start_date' not in klines_settings_with_dates:
                klines_settings_with_dates['start_date'] = simulation_settings['start_date']
            if simulation_settings.get('end_date') and 'end_date' not in klines_settings_with_dates:
                klines_settings_with_dates['end_date'] = simulation_settings['end_date']
            
            data["klines"] = self.kline_loader.load_multiple_terms(stock_id, klines_settings_with_dates)
            
            # 确保返回dict类型
            if not isinstance(data.get("klines"), dict):
                data["klines"] = {}
            
            # 加载股票标签数据（如果配置）
            if klines_settings.get('stock_labels', False):
                data["stock_labels"] = self._load_stock_labels_data_for_simulation(stock_id, klines_settings)
            
            # 应用技术指标（如果配置）
            if data["klines"] and klines_settings.get('indicators'):
                from app.analyzer.components.indicators import Indicators
                data["klines"] = Indicators.add_indicators(data["klines"], klines_settings['indicators'])
        
        # 2. 加载宏观数据
        macro_settings = settings.get("macro")
        if macro_settings:
            data["macro"] = self._load_macro_data(macro_settings)
        
        # 3. 加载企业财务数据
        corporate_finance_settings = settings.get("corporate_finance")
        if corporate_finance_settings:
            data["corporate_finance"] = self._load_corporate_finance_data(stock_id, corporate_finance_settings)
        
        # 4. 加载指数指标数据
        index_indicators_settings = settings.get("index_indicators")
        if index_indicators_settings:
            data["index_indicators"] = self._load_index_indicators_data(index_indicators_settings)
        
        # 5. 加载行业资金流数据
        industry_capital_flow_settings = settings.get("industry_capital_flow")
        if industry_capital_flow_settings:
            data["industry_capital_flow"] = self._load_industry_capital_flow_data(industry_capital_flow_settings)
        
        return data
    
    def _load_stock_labels_data_for_simulation(self, stock_id: str, klines_settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        为模拟器加载股票标签数据（一次性加载所有历史标签，按日期升序）
        
        Args:
            stock_id: 股票代码
            klines_settings: K线设置（包含模拟时间范围等信息）
            
        Returns:
            Dict: 按日期分组的标签数据，格式为 {date: [label_objects]}
        """
        try:
            # 获取模拟时间范围
            simulation_settings = klines_settings.get('simulation', {})
            start_date = simulation_settings.get('start_date')
            end_date = simulation_settings.get('end_date')
            
            # 验证必要的时间范围配置
            if not start_date:
                # 使用默认开始日期
                start_date = DateUtils.DEFAULT_START_DATE
            if not end_date:
                end_date = DateUtils.get_current_date_str()  # 只有end_date可以使用当前日期作为默认值
            
            # 一次性获取时间范围内的所有标签数据
            all_labels = self.label_loader.get_stock_labels_by_date_range(stock_id, start_date, end_date)
            
            # 按日期分组标签数据，只保存标签ID
            labels_by_date = {}
            for label_record in all_labels:
                date = label_record.get('date')
                label_id = label_record.get('label_id')
                if date and label_id:
                    if date not in labels_by_date:
                        labels_by_date[date] = []
                    labels_by_date[date].append(label_id)
            
            # 按日期排序
            sorted_labels = dict(sorted(labels_by_date.items()))
            
            return sorted_labels
            
        except Exception as e:
            logger.error(f"加载股票标签数据失败 {stock_id}: {e}")
            return {}
    
    @staticmethod
    def filter_labels_by_category(all_labels: List[str], target_categories: List[str]) -> Dict[str, List[str]]:
        """
        静态方法：按标签种类过滤标签
        
        Args:
            all_labels: 所有标签ID列表
            target_categories: 目标标签种类列表（如 ['market_cap', 'volatility']）
            
        Returns:
            Dict: 按种类分组的标签，格式为 {category: [label_ids]}
        """
        try:
            from app.labeler.conf.label_mapping import LabelMapping
            label_mapping = LabelMapping()
            
            filtered_labels = {}
            for category in target_categories:
                # 获取该分类的所有可能标签
                category_labels = label_mapping.get_labels_by_category(category)
                if category_labels:
                    # 过滤出属于该分类的标签
                    category_filtered = []
                    for label in all_labels:
                        if label in category_labels:
                            category_filtered.append(label)
                    filtered_labels[category] = category_filtered
            
            return filtered_labels
            
        except Exception as e:
            logger.error(f"按种类过滤标签失败: {e}")
            return {}
    
    # ============ 标签相关方法 ============
    
    def get_stock_labels(self, stock_id: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取股票在指定日期的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 标签ID列表
        """
        return self.label_loader.get_stock_labels(stock_id, target_date)
    
    def save_stock_labels(self, stock_id: str, label_date: str, labels: List[str]):
        """
        保存股票标签
        
        Args:
            stock_id: 股票代码
            label_date: 标签日期 (YYYY-MM-DD)
            labels: 标签ID列表
        """
        return self.label_loader.save_stock_labels(stock_id, label_date, labels)
    
    def get_stocks_with_label(self, label_id: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取具有指定标签的股票列表
        
        Args:
            label_id: 标签ID
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 股票代码列表
        """
        return self.label_loader.get_stocks_with_label(label_id, target_date)
    
    def get_label_statistics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            Dict: 统计信息
        """
        return self.label_loader.get_label_statistics(target_date)
    
    # ============ 私有方法（委托给子loaders）============
    
    def _load_macro_data(self, macro_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        加载宏观数据（委托给MacroEconomyLoader）
        
        Args:
            macro_settings: 宏观数据配置，例如：
                {
                    "GDP": True,
                    "LPR": True,
                    "Shibor": True,
                    "price_indexes": ["CPI", "PPI", "PMI", "MoneySupply"],
                    "start_date": "20200101",
                    "end_date": "20241231"
                }
        
        Returns:
            Dict: 包含各类宏观数据的字典
        """
        result = {}
        
        # 提取通用的日期参数（空字符串视为None，表示不限制）
        start_date = macro_settings.get('start_date')
        end_date = macro_settings.get('end_date')
        if start_date == '':
            start_date = None
        if end_date == '':
            end_date = None
        
        # 处理GDP数据（季度数据，需要转换日期格式）
        if macro_settings.get('GDP'):
            try:
                start_quarter = self._convert_date_to_quarter(start_date) if start_date else None
                end_quarter = self._convert_date_to_quarter(end_date) if end_date else None
                result['gdp'] = self.macro_loader.load_gdp(start_quarter, end_quarter)
            except Exception as e:
                logger.error(f"加载GDP数据失败: {e}")
                result['gdp'] = []
        
        # 处理LPR数据
        if macro_settings.get('LPR'):
            try:
                result['lpr'] = self.macro_loader.load_lpr(start_date, end_date)
            except Exception as e:
                logger.error(f"加载LPR数据失败: {e}")
                result['lpr'] = []
        
        # 处理Shibor数据
        if macro_settings.get('Shibor'):
            try:
                result['shibor'] = self.macro_loader.load_shibor(start_date, end_date)
            except Exception as e:
                logger.error(f"加载Shibor数据失败: {e}")
                result['shibor'] = []
        
        # 处理价格指数数据
        price_indexes = macro_settings.get('price_indexes', [])
        if price_indexes:
            # 转换日期格式：YYYYMMDD -> YYYYMM（价格指数是月度数据）
            month_start = start_date[:6] if start_date and len(start_date) >= 6 else None
            month_end = end_date[:6] if end_date and len(end_date) >= 6 else None
            
            for index_type in price_indexes:
                try:
                    if index_type == 'CPI':
                        result['cpi'] = self.macro_loader.load_cpi(month_start, month_end)
                    elif index_type == 'PPI':
                        result['ppi'] = self.macro_loader.load_ppi(month_start, month_end)
                    elif index_type == 'PMI':
                        result['pmi'] = self.macro_loader.load_pmi(month_start, month_end)
                    elif index_type == 'MoneySupply':
                        result['money_supply'] = self.macro_loader.load_money_supply(month_start, month_end)
                except Exception as e:
                    logger.error(f"加载{index_type}数据失败: {e}")
                    result[index_type.lower()] = []
        
        return result
    
    @staticmethod
    def _convert_date_to_quarter(date_str: str) -> Optional[str]:
        """
        将日期字符串转换为季度格式
        
        Args:
            date_str: 日期字符串（YYYYMMDD格式）
            
        Returns:
            季度字符串（YYYYQ[1-4]格式）或None
        """
        if not date_str or len(date_str) < 6:
            return None
        
        year = date_str[:4]
        month = date_str[4:6]
        
        # 根据月份确定季度
        month_int = int(month)
        if 1 <= month_int <= 3:
            quarter = 'Q1'
        elif 4 <= month_int <= 6:
            quarter = 'Q2'
        elif 7 <= month_int <= 9:
            quarter = 'Q3'
        else:
            quarter = 'Q4'
        
        return f"{year}{quarter}"
    
    def _load_corporate_finance_data(self, stock_id: str, corporate_finance_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        加载企业财务数据（委托给CorporateFinanceLoader）
        
        Args:
            stock_id: 股票代码
            corporate_finance_settings: 企业财务数据配置，例如：
                {
                    "categories": ["growth", "profit", "cashflow", "solvency", "operation", "asset"],
                    "start_date": "20200101",
                    "end_date": "20241231"
                }
        
        Returns:
            Dict: 包含各类企业财务数据的字典
        """
        categories = corporate_finance_settings.get('categories', [])
        start_date = corporate_finance_settings.get('start_date')
        end_date = corporate_finance_settings.get('end_date')
        # 空字符串视为None，表示不限制
        if start_date == '':
            start_date = None
        if end_date == '':
            end_date = None
        
        return self.corporate_finance_loader.load(stock_id, categories, start_date, end_date)
    
    def _load_index_indicators_data(self, index_indicators_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加载指数指标数据（委托给KlineLoader）"""
        return self.kline_loader.load_index_indicators_data(index_indicators_settings)
    
    def _load_industry_capital_flow_data(self, industry_capital_flow_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加载行业资金流数据（委托给KlineLoader）"""
        return self.kline_loader.load_industry_capital_flow_data(industry_capital_flow_settings)
    
    def load_stock_list(self, 
                       filtered: bool = False,
                       industry: str = None,
                       stock_type: str = None,
                       exchange_center: str = None,
                       order_by: str = 'id') -> List[Dict[str, Any]]:
        """
        加载股票列表
        
        Args:
            filtered: 是否使用过滤规则加载（默认False，排除ST、科创板等）
            industry: 按行业过滤（可选）
            stock_type: 按股票类型过滤（可选）
            exchange_center: 按交易所过滤（可选）
            order_by: 排序字段
            
        Returns:
            List[Dict]: 股票列表
            
        示例：
            # 加载过滤后的股票列表（默认，推荐）
            stocks = loader.load_stock_list(filtered=True)
            
            # 加载所有股票（不过滤）
            stocks = loader.load_stock_list(filtered=False)
            
            # 加载特定行业
            stocks = loader.load_stock_list(industry='银行')
            
            # 加载特定交易所
            stocks = loader.load_stock_list(exchange_center='SSE')
        """
        # 使用 StockDataService 获取股票列表（业务逻辑层）
        stock_service = self.get_data_service('stock_related.stock')
        
        if not stock_service:
            # 如果 Service 未初始化，降级到 Model 层（向后兼容）
            stock_list_model = self.get_model('stock_list')
            if industry:
                return stock_list_model.load_by_industry(industry, order_by)
            elif stock_type:
                return stock_list_model.load_by_type(stock_type, order_by)
            elif exchange_center:
                return stock_list_model.load_by_exchange_center(exchange_center, order_by)
            elif filtered:
                # 降级：直接使用 Service 的过滤方法（如果可能）
                logger.warning("StockDataService 未初始化，使用 Model 层（过滤功能不可用）")
                return stock_list_model.load_active_stocks()
            else:
                return stock_list_model.load_active_stocks()
        
        # 优先使用简单条件过滤（性能更好）
        if industry:
            stock_list_model = self.get_model('stock_list')
            return stock_list_model.load_by_industry(industry, order_by)
        elif stock_type:
            stock_list_model = self.get_model('stock_list')
            return stock_list_model.load_by_type(stock_type, order_by)
        elif exchange_center:
            stock_list_model = self.get_model('stock_list')
            return stock_list_model.load_by_exchange_center(exchange_center, order_by)
        elif filtered:
            # 使用 Service 层的过滤规则（业务逻辑）
            return stock_service.load_filtered_stock_list(exclude_patterns=None, order_by=order_by)
        else:
            # 加载所有活跃股票（不过滤）
            return stock_service.load_all_stocks()
    
    def load_klines(self, stock_id: str, term: str = 'daily',
                    start_date: Optional[str] = None, end_date: Optional[str] = None,
                    adjust: str = 'qfq', filter_negative: bool = True,
                    as_dataframe: bool = False) -> Union[pd.DataFrame, List[Dict]]:
        """
        加载K线数据（委托给KlineLoader）
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权方式（qfq前复权/hfq后复权/none不复权）
            filter_negative: 是否过滤负值（默认True）
            as_dataframe: 是否返回DataFrame（默认False返回List[Dict]）
            
        Returns:
            DataFrame or List[Dict]: K线数据
        """
        return self.kline_loader.load(
            stock_id, term, start_date, end_date, adjust, filter_negative, as_dataframe
        )
    
    def load_qfq_klines(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载前复权（QFQ）K线数据（使用新的 adj_factor_event 表）
        
        使用新的 adj_factor_event 表计算前复权价格：
        qfq_price = raw_price + constantDiff
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly，默认 daily）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD，可选）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD，可选）
        
        Returns:
            List[Dict]: 前复权K线数据列表，每条记录包含原始字段 + qfq_* 字段：
                - 原始字段：id, term, date, open, close, high, low, pre_close, ...
                - 前复权字段：qfq_open, qfq_close, qfq_high, qfq_low, qfq_pre_close
        
        示例:
            # 加载平安银行的前复权日线数据
            qfq_klines = data_manager.load_qfq_klines('000001.SZ', 'daily', '20240101', '20241231')
            for kline in qfq_klines:
                print(f"{kline['date']}: 原始收盘价={kline['close']}, 前复权收盘价={kline['qfq_close']}")
        """
        stock_service = self.get_data_service('stock_related.stock')
        if stock_service:
            return stock_service.load_qfq_klines(stock_id, term, start_date, end_date)
        else:
            logger.warning("StockDataService 未初始化，无法加载前复权K线数据")
            return []
    
    def get_stock_with_latest_price(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息和最新价格
        
        跨表业务方法，组合stock_list和stock_kline的数据
        
        Args:
            stock_id: 股票ID
            
        Returns:
            Dict: {
                'id': 股票ID,
                'name': 股票名称,
                'industry': 行业,
                'current_price': 最新收盘价,
                'current_price_date': 最新价格日期,
                'market_cap': 市值,
                'pe': PE,
                'pb': PB,
                'total_share': 总股本,
                'float_share': 流通股本,
                'turnover_vol': 成交量,
                'turnover_value': 成交额,
                'high': 最高价,
                'low': 最低价,
                'open': 开盘价,
                'close': 收盘价,
                ...
            }
        """
        # 1. 获取股票基本信息
        stock_list_model = self.get_model('stock_list')
        stock_info = stock_list_model.load_one("id = %s", (stock_id,))
        
        if not stock_info:
            return None
        
        result = {
            'id': stock_info.get('id'),
            'name': stock_info.get('name'),
            'industry': stock_info.get('industry'),
        }
        
        # 2. 获取最新K线数据
        kline_model = self.get_model('stock_kline')
        latest_kline = kline_model.load_one(
            "id = %s AND term = %s",
            (stock_id, 'daily'),
            order_by="date DESC"
        )
        
        if latest_kline:
            result.update({
                'current_price': latest_kline.get('close'),
                'current_price_date': latest_kline.get('date'),
                'market_cap': latest_kline.get('total_market_value'),  # 总市值
                'pe': latest_kline.get('pe'),
                'pb': latest_kline.get('pb'),
                'total_share': latest_kline.get('total_share'),
                'float_share': latest_kline.get('float_share'),
                'turnover_vol': latest_kline.get('volume'),  # 成交量
                'turnover_value': latest_kline.get('amount'),  # 成交额（字段名是amount）
                'turnover_rate': latest_kline.get('turnover_rate'),  # 换手率
                'high': latest_kline.get('highest'),  # 最高价
                'low': latest_kline.get('lowest'),    # 最低价
                'open': latest_kline.get('open'),
                'close': latest_kline.get('close'),
            })
        
        return result
    
    # ==================== 交易日相关方法 ====================
    
    def get_latest_trading_date(self) -> str:
        """
        获取最新交易日
        
        使用 TradingDateCache 获取最新交易日，支持缓存和自动刷新
        
        Returns:
            最新交易日（YYYYMMDD）
            
        示例：
            latest_date = data_manager.get_latest_trading_date()
        """
        if not self._trading_date_cache:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._trading_date_cache.get_latest_trading_date()
    
    def refresh_trading_date(self) -> str:
        """
        强制刷新最新交易日（忽略缓存）
        
        Returns:
            最新交易日（YYYYMMDD）
        """
        if not self._trading_date_cache:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._trading_date_cache.refresh()
    
    @property
    def trading_date_cache(self):
        """
        获取 TradingDateCache 实例（直接访问）
        
        Returns:
            TradingDateCache 实例
        """
        if not self._trading_date_cache:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._trading_date_cache