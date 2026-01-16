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
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, Type
import pandas as pd
from loguru import logger
import threading
import importlib
import importlib.util
import pkgutil
import inspect
from pathlib import Path

from core.infra.db.db_manager import DatabaseManager

if TYPE_CHECKING:
    from core.global_enums.enums import EntityType
# Loaders 已废弃，不再导入
# 所有功能已迁移到 data_services
from core.infra.project_context import ConfigManager
from core.utils.date.date_utils import DateUtils


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
        from core.modules.data_manager import DataManager

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
                # 检测是否是子进程（多进程场景），如果是则使用只读模式（避免写锁冲突）
                import multiprocessing
                is_child_process = multiprocessing.current_process().name != 'MainProcess'
                read_only = is_child_process
                
                if self.is_verbose:
                    if read_only:
                        logger.info("🔧 初始化 DatabaseManager（只读模式，子进程环境）...")
                    else:
                        logger.info("🔧 初始化 DatabaseManager...")
                
                try:
                    self.db = DatabaseManager(is_verbose=self.is_verbose, read_only=read_only)
                    self.db.initialize()
                    # 设置为默认实例，便于 DbBaseModel 等自动获取 db
                    DatabaseManager.set_default(self.db)
                except Exception as db_error:
                    # 在子进程环境下，如果 DuckDB 文件锁冲突，跳过 DB 初始化
                    # 这允许 compute-only worker 在不访问 DB 的情况下运行
                    error_msg = str(db_error)
                    if is_child_process and ("Could not set lock" in error_msg or "Conflicting lock" in error_msg):
                        logger.warning(
                            f"⚠️  子进程 DB 初始化失败（文件锁冲突），跳过 DB 连接: {error_msg}\n"
                            f"   这通常发生在 compute-only worker 场景，worker 将使用预加载的内存数据。"
                        )
                        # 创建一个虚拟的 DatabaseManager，但不初始化连接
                        # 这样 DataManager 的其他部分仍然可以工作（虽然不能访问 DB）
                        self.db = None
                        # 标记为已初始化，避免重复尝试
                        self._initialized = True
                        return
                    else:
                        raise
            else:
                if self.is_verbose:
                    logger.info("🔧 使用已提供的 DatabaseManager 实例...")

            # 2. 创建所有 Base Tables（业务逻辑）
            # 注意：只读模式下跳过表创建（子进程只需要读取，不需要创建表）
            if not self.db.read_only:
                if self.is_verbose:
                    logger.info("🔧 创建 Base Tables...")
                self.db.schema_manager.create_all_tables(self.db.get_connection)
            elif self.is_verbose:
                logger.info("ℹ️  只读模式，跳过 Base Tables 创建")

            # 3. 自动发现并缓存 Base Tables
            if self.is_verbose:
                logger.info("🔧 自动发现 Base Tables...")
            self._discover_base_tables()

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
    
    def register_table(self, table_folder_path: str) -> Optional[Type[Any]]:
        """
        注册表（从文件夹路径加载）
        
        表文件夹结构：
        - schema.json: 表结构定义
        - model.py: 继承自 DbBaseModel 的 Model 类
        
        Args:
            table_folder_path: 表文件夹路径（例如 'app/core/modules/data_manager/base_tables/stock_kline'）
        
        Returns:
            Model 类（继承自 DbBaseModel），如果注册失败返回 None
        
        Example:
            # 注册自定义表
            model_class = data_mgr.register_table('app/userspace/tables/my_table')
            if model_class:
                model = model_class()  # 创建实例
        """
        from core.infra.db import DbBaseModel
        from core.infra.project_context import FileManager
        
        try:
            table_folder = Path(table_folder_path)
            if not table_folder.is_absolute():
                # 尝试相对于项目根目录
                table_folder = Path.cwd() / table_folder
            
            if not table_folder.exists() or not table_folder.is_dir():
                logger.error(f"❌ 表文件夹不存在: {table_folder_path}")
                return None
            
            # 1. 查找 schema.json
            schema_file = table_folder / "schema.json"
            if not schema_file.exists():
                logger.error(f"❌ 表文件夹中未找到 schema.json: {table_folder_path}")
                return None
            
            # 2. 查找 model.py
            model_file_path = FileManager.find_file(
                "model.py",
                table_folder,
                recursive=False
            )
            if not model_file_path:
                logger.error(f"❌ 表文件夹中未找到 model.py: {table_folder_path}")
                return None
            
            # 3. 从文件路径加载模块
            try:
                spec = importlib.util.spec_from_file_location("table_model", model_file_path)
                if spec is None or spec.loader is None:
                    logger.error(f"❌ 无法加载模块: {model_file_path}")
                    return None
                
                model_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(model_module)
                
                # 4. 查找继承自 DbBaseModel 的类
                model_class = None
                for name, obj in inspect.getmembers(model_module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, DbBaseModel) and
                        obj != DbBaseModel):
                        model_class = obj
                        break
                
                if model_class is None:
                    logger.error(f"❌ 模块中未找到继承自 DbBaseModel 的类: {model_file_path}")
                    return None
                
                # 5. 从 schema.json 读取表名
                import json
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    table_name = schema.get('name')
                    if not table_name:
                        logger.error(f"❌ schema.json 中未找到表名: {schema_file}")
                        return None
                
                # 6. 缓存 Model 类
                if table_name in self._table_cache:
                    existing_class = self._table_cache[table_name]
                    if existing_class != model_class:
                        logger.warning(
                            f"⚠️  覆盖已存在的 Table '{table_name}': "
                            f"{existing_class.__name__} -> {model_class.__name__}"
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
    
    def _discover_base_tables(self):
        """
        自动发现并缓存所有 Base Tables
        
        扫描 base_tables/ 目录下的所有子目录，使用 register_table 注册每个表。
        
        注意：此方法只在初始化时调用一次，结果缓存在 _table_cache 中
        """
        try:
            # 获取 base_tables 目录的绝对路径
            base_tables_package = importlib.import_module('core.modules.data_manager.base_tables')
            package_paths = base_tables_package.__path__
            base_tables_dir = Path(package_paths[0]).resolve()
            
            # 遍历所有子目录
            for table_folder in base_tables_dir.iterdir():
                if not table_folder.is_dir() or table_folder.name.startswith('_'):
                    continue
                
                # 使用 register_table 注册表
                model_class = self.register_table(str(table_folder))
                if model_class is None:
                    if self.is_verbose:
                        logger.debug(f"  ⚠️  跳过目录（无有效表）: {table_folder.name}")
                    continue
            
            if self.is_verbose:
                logger.info(f"✅ 自动发现并缓存了 {len(self._table_cache)} 个 Base Tables")
                
        except Exception as e:
            logger.error(f"❌ 自动发现 Base Tables 失败: {e}")
            raise
    
    # ------------------------------------------------------------------
    # Table 访问（基础表 + 自定义表）
    # ------------------------------------------------------------------

    def get_table(self, table_name: str) -> Any:
        """
        获取指定表对应的 Model 实例（内部方法，仅供 DataService 使用）
        
        Args:
            table_name: 表名，例如 'stock_kline'、'stock_list' 等（Base Tables）
                       或用户自定义的表名（需先通过 register_table 注册）
            
        Returns:
            对应的 Model 实例（已自动绑定默认 db），如果未找到则返回 None
        """
        # 从缓存中获取 Model 类
        model_class = self._table_cache.get(table_name)
        
        if not model_class:
            logger.warning(f"⚠️  表 '{table_name}' 没有对应的 Model 类（可能未注册）")
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
        跨service协调器（属性访问）
        
        用于跨service方法，如 prepare_data
        
        Returns:
            DataService 实例
        """
        if not self._data_service:
            raise RuntimeError("DataManager 未初始化，请先调用 initialize()")
        return self._data_service