#!/usr/bin/env python3
"""
数据管理服务 - 统一的数据访问层

职责：
- 管理 DatabaseManager（唯一持有者）
- 初始化数据库和表结构
- 提供统一的数据访问 API
- 协调各个 DataService

架构：
- DataManager: 数据访问层入口，管理 DB 和 DataServices
- DataServices: 数据服务层（stock, macro, calendar, ui_transit）
  - StockService: 股票数据服务（K线、股票列表、标签、财务等）
  - MacroService: 宏观经济数据服务
  - CalendarService: 交易日历服务
  - CorporateFinanceService: 企业财务数据服务（StockService 的子服务）
"""
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING
import pandas as pd
from loguru import logger
import threading

from app.core.infra.db.db_manager import DatabaseManager

if TYPE_CHECKING:
    from app.core.global_enums.enums import EntityType
# Loaders 已废弃，不再导入
# 所有功能已迁移到 data_services
from app.core.conf.conf import data_default_start_date
from app.core.utils.date.date_utils import DateUtils


class DataManager:
    """
    数据管理服务（数据访问总入口）

    职责：
    - 唯一持有和管理 DatabaseManager
    - 初始化数据库、连接池、表结构（Base Tables + 策略表）
    - 提供统一的数据访问 API（对应用/策略暴露的门面）
    - 协调各 DataService（stock, macro, calendar, ui_transit）
    - 预留 Repository / 策略表 Model 的注册与访问能力（新架构方向）

    单例模式：
    - 单进程环境下：使用同一个实例（线程安全）
    - 多进程环境下：每个进程有独立的实例（进程间内存不共享）
    - 支持通过 force_new=True 强制创建新实例

    使用方式：
        from app.core.modules.data_manager import DataManager

        # 自动使用单例（推荐）
        data_mgr = DataManager(is_verbose=True)
        data = data_mgr.service.prepare_data(stock, settings)
        
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

        # DataService 主类（跨service协调器）
        self._data_service = None

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
        3. 初始化所有 DataServices
        
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

            # 3. 初始化 DataService（跨service协调器）
            if self.is_verbose:
                logger.info("🔧 初始化 DataService...")
            from app.core.modules.data_manager.data_services import DataService
            self._data_service = DataService(self)

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
        获取指定表对应的 Model 实例（内部方法，仅供 DataService 使用）
        
        ⚠️ 警告：此方法仅供 DataManager 内部和 DataService 使用，外部代码不应直接调用！
        
        外部代码应通过 DataService 层访问数据：
            # ✅ 正确方式
            klines = data_mgr.stock.load_klines('000001.SZ', start_date='20200101')
            
            # ❌ 错误方式（不要这样做）
            # kline_model = data_mgr.get_model('stock_kline')
            # klines = kline_model.load_by_date_range(...)
        
        返回的是个性化 Model（如 StockKlineModel），而不是 DbBaseModel
        
        Args:
            table_name: 表名，例如 'stock_kline'、'stock_list' 等
            
        Returns:
            对应的 Model 实例（已自动绑定默认 db）
        """
        # 表名到 Model 类的映射
        from app.core.modules.data_manager.base_tables import (
            StockKlineModel, StockListModel, AdjFactorEventModel,
            GdpModel, PriceIndexesModel, ShiborModel, LprModel,
            CorporateFinanceModel, StockIndexIndicatorModel, StockIndexIndicatorWeightModel,
            SystemCacheModel, TagScenarioModel, TagDefinitionModel, TagValueModel
        )
        
        model_map = {
            'stock_list': StockListModel,
            'stock_kline': StockKlineModel,
            'adj_factor_event': AdjFactorEventModel,
            'gdp': GdpModel,
            'price_indexes': PriceIndexesModel,
            'shibor': ShiborModel,
            'lpr': LprModel,
            'corporate_finance': CorporateFinanceModel,
            'stock_index_indicator': StockIndexIndicatorModel,
            'stock_index_indicator_weight': StockIndexIndicatorWeightModel,
            'system_cache': SystemCacheModel,
            'tag_scenario': TagScenarioModel,
            'tag_definition': TagDefinitionModel,
            'tag_value': TagValueModel,
        }
        
        model_class = model_map.get(table_name)
        if not model_class:
            logger.warning(f"表 '{table_name}' 没有对应的 Model 类")
            return None
        
        # 返回 Model 实例（自动获取默认 db）
        return model_class()

    # ------------------------------------------------------------------
    # DataService 属性访问
    # ------------------------------------------------------------------
    
    @property
    def stock(self):
        """
        股票数据服务（属性访问）
        
        Returns:
            StockService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service.stock
    
    @property
    def macro(self):
        """
        宏观经济数据服务（属性访问）
        
        Returns:
            MacroService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service.macro
    
    @property
    def calendar(self):
        """
        日期服务（属性访问）
        
        Returns:
            CalendarService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service.calendar
    
    @property
    def service(self):
        """
        跨service协调器（属性访问）
        
        用于跨service方法，如 prepare_data
        
        Returns:
            DataService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service
    
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