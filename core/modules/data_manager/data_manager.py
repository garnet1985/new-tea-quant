#!/usr/bin/env python3
"""
数据管理服务 - 统一的数据访问层（driver）

职责：
- 管理 DatabaseManager（唯一持有者）
- 初始化数据库和表结构
- 提供统一的数据访问 API（get_table 等）
- 协调各个 DataService

表名定义：
-   表名由 DataManager 配合 PathManager 发现（core/tables、userspace/tables），
  core 表须 sys_ 前缀，userspace 表无前缀限制；get_table(table_name) 使用实际表名字符串。

架构：
- DataManager: 数据访问层入口，管理 DB 和 DataServices
- DataServices: 数据服务层（stock, macro, calendar, ui_transit）
  - StockService: 股票数据服务（K线、股票列表、标签、财务等）
  - MacroService: 宏观经济数据服务
  - CalendarService: 交易日历服务
  - CorporateFinanceService: 企业财务数据服务（StockService 的子服务）
"""
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, Type
import pandas as pd
import logging
import threading
import importlib
import importlib.util
import pkgutil
import inspect
from pathlib import Path

from core.infra.db import DatabaseManager

if TYPE_CHECKING:
    from core.global_enums.enums import EntityType
# Loaders 已废弃，不再导入
# 所有功能已迁移到 data_services
from core.infra.project_context import ConfigManager
from core.utils.date.date_utils import DateUtils


logger = logging.getLogger(__name__)


class DataManager:
    """
    数据管理服务（数据访问总入口，driver）

    职责：
    - 唯一持有和管理 DatabaseManager
    - 初始化数据库、连接池、表结构（Base Tables + 策略表）
    - 提供统一的数据访问 API（get_table 等；表名即发现并注册后的实际表名）
    - 协调各 DataService（stock, macro, calendar, ui_transit）
    - 预留 Repository / 策略表 Model 的注册与访问能力（新架构方向）

    单例模式：
    - 单进程环境下：使用同一个实例（线程安全）
    - 多进程环境下：每个进程有独立的实例（进程间内存不共享）
    - 支持通过 force_new=True 强制创建新实例

    使用方式：
        from core.modules.data_manager import DataManager

        # 自动使用单例（推荐）
        data_mgr = DataManager(is_verbose=True)
        data_mgr.initialize()
        klines = data_mgr.stock.kline.load('000001.SZ', term='daily', adjust='qfq')

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

        # Table 缓存（table_name -> Model 类）
        # Base Tables 自动发现，用户自定义 Tables 通过 register_table 注册
        self._table_cache: Dict[str, Type[Any]] = {}
        
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
            if self.db:
                if self.is_verbose:
                    logger.info("🔧 创建 Base Tables...")
                self.db.schema_manager.create_all_tables(self.db.get_connection)
            elif self.is_verbose:
                logger.info("ℹ️  只读模式，跳过 Base Tables 创建")

            # 3. 自动发现并缓存表（core/tables -> sys_*，userspace/tables -> cust_*）
            if self.is_verbose:
                logger.info("🔧 自动发现表（core/tables + userspace/tables）...")
            self._discover_tables()

            # 4. 初始化 DataService（跨service协调器）
            if self.is_verbose:
                logger.info("🔧 初始化 DataService...")
            from core.modules.data_manager.data_services import DataService
            self._data_service = DataService(self)

            self._initialized = True
            
            if self.is_verbose:
                logger.info("✅ DataManager 初始化完成")
                
        except Exception as e:
            logger.error(f"❌ DataManager 初始化失败: {e}")
            raise

    # ------------------------------------------------------------------
    # Table 发现与注册
    # ------------------------------------------------------------------
    
    def register_table(self, table_folder_path: str, from_core: bool = False) -> Optional[Type[Any]]:
        """
        注册表（从文件夹路径加载，配合 PathManager 发现的目录）。
        
        表文件夹结构：schema.py + model.py，表名取自 schema["name"]。
        
        Args:
            table_folder_path: 表文件夹路径（core/tables/xxx 或 userspace/tables/xxx）
            from_core: 若为 True 表示来自 core/tables，则 schema["name"] 须以 sys_ 开头，否则跳过
        
        Returns:
            Model 类（继承自 DbBaseModel），若校验不通过或加载失败返回 None
        """
        from core.infra.db import DbBaseModel
        from core.infra.project_context import FileManager
        from core.infra.db.schema_management.schema_manager import SchemaManager
        
        try:
            table_folder = Path(table_folder_path)
            if not table_folder.is_absolute():
                table_folder = Path.cwd() / table_folder
            
            if not table_folder.exists() or not table_folder.is_dir():
                logger.error(f"❌ 表文件夹不存在: {table_folder_path}")
                return None
            
            # 1. 加载 schema（仅 schema.py）
            schema_py = table_folder / "schema.py"
            if not schema_py.exists():
                logger.error(f"❌ 表文件夹中未找到 schema.py: {table_folder_path}")
                return None
            schema_manager = SchemaManager()
            schema = schema_manager.load_schema_from_python(str(schema_py))
            if not schema:
                return None
            
            table_name = schema.get("name")
            if not table_name:
                logger.error(f"❌ schema 中未找到 name: {table_folder_path}")
                return None
            if from_core and not table_name.startswith("sys_"):
                if self.is_verbose:
                    logger.debug(f"⏭️  跳过 core 表（非 sys_ 前缀）: {table_name} ({table_folder_path})")
                return None
            
            # 2. 查找并加载 model.py
            model_file_path = FileManager.find_file("model.py", table_folder, recursive=False)
            if not model_file_path:
                logger.error(f"❌ 表文件夹中未找到 model.py: {table_folder_path}")
                return None
            
            try:
                spec = importlib.util.spec_from_file_location("table_model", model_file_path)
                if spec is None or spec.loader is None:
                    logger.error(f"❌ 无法加载模块: {model_file_path}")
                    return None
                model_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(model_module)
                
                model_class = None
                for name, obj in inspect.getmembers(model_module):
                    if (inspect.isclass(obj) and issubclass(obj, DbBaseModel) and obj != DbBaseModel):
                        model_class = obj
                        break
                if model_class is None:
                    logger.error(f"❌ 模块中未找到继承自 DbBaseModel 的类: {model_file_path}")
                    return None
                
                if table_name in self._table_cache and self._table_cache[table_name] != model_class:
                    logger.warning(
                        f"⚠️  覆盖已存在的 Table '{table_name}': "
                        f"{self._table_cache[table_name].__name__} -> {model_class.__name__}"
                    )
                self._table_cache[table_name] = model_class
                if self.is_verbose:
                    logger.info(f"✅ 注册 Table: {table_name} -> {model_class.__name__} ({table_folder_path})")
                return model_class
            except Exception as e:
                logger.error(f"❌ 加载模块失败: {model_file_path}, error={e}")
                return None
        except Exception as e:
            logger.error(f"❌ 注册 Table 失败: {table_folder_path}, error={e}")
            return None
    
    def _discover_tables(self):
        """
        配合 PathManager 递归发现 core/tables 与 userspace/tables 下的表并缓存。
        不依赖目录层级：递归查找所有 schema.py，以其所在目录为表目录并注册。
        - core/tables：仅注册 schema["name"] 以 sys_ 开头的表，否则跳过。
        - userspace/tables：表名无前缀限制，全部注册。
        仅在初始化时调用一次，结果缓存在 _table_cache 中。
        """
        from core.infra.project_context import PathManager

        def _dirs_with_schema(root: Path) -> set:
            """递归收集包含 schema.py 的目录。"""
            return {p.parent for p in root.rglob("schema.py") if p.is_file()}

        try:
            # 1. core/tables（仅接受 sys_ 前缀）
            core_tables_dir = PathManager.core() / "tables"
            if core_tables_dir.exists():
                for table_folder in sorted(_dirs_with_schema(core_tables_dir)):
                    self.register_table(str(table_folder), from_core=True)

            # 2. userspace/tables（表名无限制）
            userspace_tables_dir = PathManager.userspace() / "tables"
            if userspace_tables_dir.exists():
                for table_folder in sorted(_dirs_with_schema(userspace_tables_dir)):
                    self.register_table(str(table_folder), from_core=False)

            if self.is_verbose:
                logger.info(f"✅ 自动发现并缓存了 {len(self._table_cache)} 个表")
        except Exception as e:
            logger.error(f"❌ 自动发现表失败: {e}")
            raise
    
    # ------------------------------------------------------------------
    # Table 访问（基础表 + 自定义表）
    # ------------------------------------------------------------------

    def get_table(self, table_name: str) -> Any:
        """
        获取指定表对应的 Model 实例（内部方法，仅供 DataService 使用）。
        
        表名由 DataManager 发现并注册（core 表 sys_ 前缀，userspace 表无限制）。
        
        Args:
            table_name: 实际表名，如 "sys_stock_list"。
            
        Returns:
            对应的 Model 实例（已自动绑定默认 db），如果未找到则返回 None
        """
        model_class = self._table_cache.get(table_name)

        if not model_class:
            logger.warning(f"⚠️  表 '{table_name}' 没有对应的 Model 类（可能未注册）")
            return None

        return model_class()

    def get_physical_table_name(self, logical_name: str) -> str:
        """
        返回逻辑表在当前数据库下的“物理表名”（用于直接写 SQL 时使用）。

        - PostgreSQL: 使用 pgsql_schema.table_name
        - MySQL: 暂时返回逻辑名本身
        """
        # 先获取 Model，看表是否已注册
        model = self.get_table(logical_name)
        if not model:
            raise ValueError(f"Unknown table: {logical_name}")

        db_type = self.db.config.get("database_type", "postgresql")

        if db_type == "postgresql":
            pg_cfg = self.db.config.get("postgresql", {})
            pg_schema = pg_cfg.get("pgsql_schema", "public")
            return f"{pg_schema}.{model.table_name}"

        # MySQL：目前直接返回逻辑名；后续如有表名前缀等需求再扩展
        return logical_name

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
    def index(self):
        """
        指数数据服务（属性访问）
        
        Returns:
            IndexService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service.index
    
    @property
    def db_cache(self):
        """
        数据库缓存服务（属性访问）
        
        Returns:
            DbCacheService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service.db_cache
    
    @property
    def service(self):
        """
        跨 service 协调器（属性访问），提供 data_mgr.stock / macro / calendar 等统一入口。

        Returns:
            DataService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service