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
- DataServices: 数据服务层（stock_related, macro_system, ui_transit）
  - StockDataService: 股票数据服务（K线、股票列表等）
  - LabelDataService: 标签数据服务
  - MacroDataService: 宏观经济数据服务
  - CorporateFinanceDataService: 企业财务数据服务
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
    - 协调各 DataService（stock_related, macro_system, ui_transit）
    - 预留 Repository / 策略表 Model 的注册与访问能力（新架构方向）

    单例模式：
    - 单进程环境下：使用同一个实例（线程安全）
    - 多进程环境下：每个进程有独立的实例（进程间内存不共享）
    - 支持通过 force_new=True 强制创建新实例

    使用方式：
        from app.core.modules.data_manager import DataManager

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
        from app.core.modules.data_manager.base_tables import (
            StockKlineModel, StockListModel, AdjFactorEventModel,
            GdpModel, PriceIndexesModel, ShiborModel, LprModel,
            CorporateFinanceModel, StockLabelsModel,
            InvestmentTradesModel, InvestmentOperationsModel,
            StockIndexIndicatorModel, StockIndexIndicatorWeightModel,
            MetaInfoModel, TagScenarioModel, TagDefinitionModel, TagValueModel
        )
        
        model_map = {
            'stock_kline': StockKlineModel,
            'stock_list': StockListModel,
            # 'adj_factor': AdjFactorModel,  # 已移除，使用 adj_factor_event 替代
            'adj_factor_event': AdjFactorEventModel,
            'gdp': GdpModel,
            'price_indexes': PriceIndexesModel,
            'shibor': ShiborModel,
            'lpr': LprModel,
            'corporate_finance': CorporateFinanceModel,
            'stock_labels': StockLabelsModel,
            'investment_trades': InvestmentTradesModel,
            'investment_operations': InvestmentOperationsModel,
            'stock_index_indicator': StockIndexIndicatorModel,
            'stock_index_indicator_weight': StockIndexIndicatorWeightModel,
            'meta_info': MetaInfoModel,
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
        
        # ========== 默认查询 ==========
        
        for data_type, config in settings.items():
            if data_type in processed:
                continue
            
            # 股票K线数据
            if data_type == 'stock_kline':
                if 'ts_code' in context and 'date' in context:
                    # TODO: 根据 config 参数调用对应的方法
                    result['stock_kline'] = self.stock.kline.load_kline_series(
                        context['ts_code'], start_date=context['date'], end_date=context['date']
                    )
            
            # 财务数据
            elif data_type == 'corporate_finance':
                if 'ts_code' in context and 'quarter' in context:
                    indicators = config.get('indicators') if isinstance(config, dict) else None
                    result['corporate_finance'] = self.stock.corporate_finance.load_financials(
                        context['ts_code'], indicators, context['quarter']
                    )
            
            # 股票标签
            elif data_type == 'stock_labels':
                if 'ts_code' in context and 'date' in context:
                    result['stock_labels'] = self.stock.load_tags(
                        context['ts_code'], date=context['date']
                    )
            
            # 宏观经济数据
            elif data_type == 'macro_economy':
                if 'date' in context:
                    # 如果配置要求完整快照
                    if isinstance(config, dict) and config.get('full_snapshot'):
                        result['macro_economy'] = self.macro.load_macro_snapshot(context['date'])
                    # 如果指定了指标
                    elif isinstance(config, dict) and 'indicators' in config:
                        result['macro_economy'] = {}
                        for indicator in config['indicators']:
                            if indicator == 'shibor':
                                result['macro_economy']['shibor'] = self.macro.load_shibor(
                                    context['date'], context['date']
                                )
                            elif indicator == 'lpr':
                                result['macro_economy']['lpr'] = self.macro.load_lpr(
                                    context['date'], context['date']
                                )
                            # 其他指标...
                    # 默认加载快照
                    else:
                        result['macro_economy'] = self.macro.load_macro_snapshot(context['date'])
            
            # 投资记录
            elif data_type == 'investment_operations':
                if 'ts_code' in context:
                    # TODO: 需要实现 InvestmentService
                    logger.warning("investment_operations 暂未实现")
                    result['investment_operations'] = []
            
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
        
        委托给 DataService.prepare_data()
        
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
        return self.service.prepare_data(stock, settings)
    
    # ============ 私有方法（委托给 DataServices）============
    
    def _load_macro_data(self, macro_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        加载宏观数据（委托给 MacroDataService）
        
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
                result['gdp'] = self.macro.load_gdp(start_quarter, end_quarter)
            except Exception as e:
                logger.error(f"加载GDP数据失败: {e}")
                result['gdp'] = []
        
        # 处理LPR数据
        if macro_settings.get('LPR'):
            try:
                result['lpr'] = self.macro.load_lpr(start_date, end_date)
            except Exception as e:
                logger.error(f"加载LPR数据失败: {e}")
                result['lpr'] = []
        
        # 处理Shibor数据
        if macro_settings.get('Shibor'):
            try:
                result['shibor'] = self.macro.load_shibor(start_date, end_date)
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
                        result['cpi'] = self.macro.load_cpi(month_start, month_end)
                    elif index_type == 'PPI':
                        result['ppi'] = self.macro.load_ppi(month_start, month_end)
                    elif index_type == 'PMI':
                        result['pmi'] = self.macro.load_pmi(month_start, month_end)
                    elif index_type == 'MoneySupply':
                        result['money_supply'] = self.macro.load_money_supply(month_start, month_end)
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
        加载企业财务数据（委托给 CorporateFinanceDataService）
        
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
        
        return self.stock.corporate_finance.load(stock_id, categories, start_date, end_date)
    
    def _load_index_indicators_data(self, index_indicators_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加载指数指标数据（暂未实现）"""
        logger.warning("_load_index_indicators_data 暂未实现")
        return {}
        
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
        # 使用 StockService 获取股票列表
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
        else:
            # 使用 Service 层的过滤规则（业务逻辑）
            return self.stock.load_stock_list(filtered=filtered, order_by=order_by)
    
    def load_entity_list(
        self,
        entity_type: 'EntityType',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **filters
    ) -> List[str]:
        """
        加载实体ID列表
        
        Args:
            entity_type: 实体类型枚举（EntityType.STOCK_KLINE_DAILY 等）
            start_date: 起始日期（可选，用于过滤有日期范围的实体）
            end_date: 结束日期（可选）
            **filters: 其他过滤条件（如 filtered, industry, stock_type 等）
            
        Returns:
            List[str]: 实体ID列表
            
        示例：
            # 加载所有股票ID
            stock_ids = data_mgr.load_entity_list(EntityType.STOCK_KLINE_DAILY)
            
            # 加载过滤后的股票ID
            stock_ids = data_mgr.load_entity_list(
                EntityType.STOCK_KLINE_DAILY,
                filtered=True
            )
        """
        from app.core.global_enums.enums import EntityType as EntityTypeEnum
        
        # 当前只支持 stock 相关的实体类型
        if entity_type in [EntityTypeEnum.STOCK_KLINE_DAILY, EntityTypeEnum.STOCK_KLINE_WEEKLY, EntityTypeEnum.STOCK_KLINE_MONTHLY]:
            # 使用 load_stock_list 加载股票列表
            filtered = filters.get('filtered', False)
            industry = filters.get('industry')
            stock_type = filters.get('stock_type')
            exchange_center = filters.get('exchange_center')
            order_by = filters.get('order_by', 'id')
            
            stock_list = self.load_stock_list(
                filtered=filtered,
                industry=industry,
                stock_type=stock_type,
                exchange_center=exchange_center,
                order_by=order_by
            )
            
            # 提取股票ID列表
            entity_list = [stock.get('id') for stock in stock_list if stock.get('id')]
            
            # TODO: 如果提供了 start_date 和 end_date，可以根据 K线数据的时间范围进一步过滤
            # 例如：只返回在指定时间范围内有交易数据的股票
            if start_date or end_date:
                # 暂时不实现时间过滤，直接返回所有股票ID
                # 未来可以实现：查询 stock_kline 表，只返回有数据的股票
                pass
            
            return entity_list
        else:
            logger.warning(f"不支持的实体类型: {entity_type}，当前只支持 STOCK_KLINE_* 类型")
            return []
    
    def load_klines(self, stock_id: str, term: str = 'daily',
                    start_date: Optional[str] = None, end_date: Optional[str] = None,
                    adjust: str = 'qfq', filter_negative: bool = True,
                    as_dataframe: bool = False) -> Union[pd.DataFrame, List[Dict]]:
        """
        加载K线数据（委托给 StockService）
        
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
        return self.stock.load_klines(
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
        加载前复权（QFQ）K线数据（委托给 StockService）
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly，默认 daily）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD，可选）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD，可选）
        
        Returns:
            List[Dict]: 前复权K线数据列表
        
        示例:
            # 加载平安银行的前复权日线数据
            qfq_klines = data_manager.load_qfq_klines('000001.SZ', 'daily', '20240101', '20241231')
        """
        return self.stock.load_qfq_klines(stock_id, term, start_date, end_date)
    
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
    
    def get_latest_completed_trading_date(self) -> str:
        """
        获取最新已完成的交易日（上一个交易日）
        
        委托给 CalendarService
        
        Returns:
            最新已完成的交易日（YYYYMMDD）
            
        示例：
            latest_date = data_manager.get_latest_completed_trading_date()
        """
        return self.calendar.get_latest_trading_date()
    
    def get_latest_trading_date(self) -> str:
        """
        已废弃：请使用 get_latest_completed_trading_date()
        
        为了向后兼容，保留此方法
        """
        return self.get_latest_completed_trading_date()
    
    def refresh_trading_date(self) -> str:
        """
        强制刷新最新交易日（忽略缓存）
        
        Returns:
            最新交易日（YYYYMMDD）
        """
        return self.calendar.refresh()
    
    @property
    def trading_date_cache(self):
        """
        获取 CalendarService 实例（向后兼容）
        
        Returns:
            CalendarService 实例
        """
        return self.calendar
    
    def get_stocks_latest_corporate_update_quarter(self) -> List[Dict[str, Any]]:
        """
        获取不在当前季度的企业财务数据股票列表
        
        查询逻辑：找出所有股票中，最新财务数据季度不等于当前季度的股票
        
        Args:
            current_quarter: 当前季度（YYYYQ[1-4]格式）
        
        Returns:
            List[Dict]: 股票列表，每个元素包含：
                - id: 股票代码
        """
        corporate_finance_model = self.get_model('corporate_finance')
        
        # 查询每个股票的最新季度
        # SQL: SELECT id, MAX(quarter) as last_updated_quarter FROM corporate_finance GROUP BY id
        query = f"""
            SELECT id, MAX(quarter) as last_updated_quarter
            FROM {corporate_finance_model.table_name}
            GROUP BY id
        """
        
        try:
            results = corporate_finance_model.db.execute_sync_query(query)

            raw_map = {}
            for row in results or []:
                stock_id = row.get("id")
                if not stock_id:
                    continue
                raw_map[stock_id] = row.get("last_updated_quarter")
            
            return raw_map
            

        except Exception as e:
            logger.error(f"查询企业财务数据股票列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []