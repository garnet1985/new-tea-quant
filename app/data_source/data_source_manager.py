"""
DataSource Manager - 数据源管理器

负责加载和管理 DataSource、Handler、Schema，执行数据获取
"""
import json
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger


class DataSourceManager:
    """
    数据源管理器
    
    职责：
    - 加载 Schema 定义
    - 加载 Handler 映射配置
    - 动态加载 Handler 类
    - 执行 Handler 获取数据
    """
    
    def __init__(self, data_manager=None, is_verbose: bool = False):
        """
        初始化数据源管理器
        
        Args:
            data_manager: DataManager 实例（可选，用于数据持久化）
            is_verbose: 是否输出详细日志
        """
        self.data_manager = data_manager
        self.is_verbose = is_verbose
        self._schemas: Dict[str, Any] = {}
        self._handlers: Dict[str, Any] = {}
        self._mapping: Dict[str, Any] = {}
        
        # 加载配置
        self._load_schemas()
        self._load_mapping()
        self._load_handlers()
    
    def _load_schemas(self):
        """加载 Schema 定义"""
        try:
            from app.data_source.defaults.schemas import DEFAULT_SCHEMAS
            self._schemas = DEFAULT_SCHEMAS.copy()
            logger.debug(f"✅ 加载了 {len(self._schemas)} 个 Schema")
        except Exception as e:
            logger.error(f"❌ 加载 Schema 失败: {e}")
            self._schemas = {}
    
    def _load_mapping(self):
        """加载 Handler 映射配置（先加载 defaults，再加载 custom 覆盖）"""
        self._mapping = {}
        
        # 1. 加载 defaults/mapping.json
        try:
            defaults_path = Path(__file__).parent / "defaults" / "mapping.json"
            if defaults_path.exists():
                with open(defaults_path, 'r', encoding='utf-8') as f:
                    defaults_mapping = json.load(f)
                    self._mapping.update(defaults_mapping.get("data_sources", {}))
                logger.debug(f"✅ 加载了 defaults/mapping.json")
        except Exception as e:
            logger.warning(f"⚠️ 加载 defaults/mapping.json 失败: {e}")
        
        # 2. 加载 custom/mapping.json（覆盖 defaults）
        try:
            custom_path = Path(__file__).parent / "custom" / "mapping.json"
            if custom_path.exists():
                with open(custom_path, 'r', encoding='utf-8') as f:
                    custom_mapping = json.load(f)
                    # 只更新已存在的或新增的 data_source
                    for ds_name, ds_config in custom_mapping.get("data_sources", {}).items():
                        if ds_config.get("is_enabled", True):
                            self._mapping[ds_name] = ds_config
                logger.debug(f"✅ 加载了 custom/mapping.json")
        except Exception as e:
            logger.debug(f"custom/mapping.json 不存在或加载失败（这是正常的）: {e}")
    
    def _load_handler(self, ds_name: str, handler_path: str):
        """
        动态加载 Handler 类
        
        Args:
            ds_name: 数据源名称
            handler_path: Handler 类的完整路径（如 "defaults.handlers.stock_list_handler.TushareStockListHandler"）
        
        Returns:
            Handler 类
        """
        try:
            module_path, class_name = handler_path.rsplit('.', 1)
            module = importlib.import_module(f"app.data_source.{module_path}")
            handler_class = getattr(module, class_name)
            return handler_class
        except Exception as e:
            logger.error(f"❌ 加载 Handler 失败 {ds_name} ({handler_path}): {e}")
            return None
    
    def _load_handlers(self):
        """加载所有启用的 Handler 实例"""
        for ds_name, ds_config in self._mapping.items():
            if not ds_config.get("is_enabled", True):
                continue
            
            handler_path = ds_config.get("handler")
            if not handler_path:
                logger.warning(f"⚠️ {ds_name} 没有配置 handler")
                continue
            
            # 获取 Schema
            schema = self._schemas.get(ds_name)
            if not schema:
                logger.warning(f"⚠️ {ds_name} 没有找到对应的 Schema")
                continue
            
            # 加载 Handler 类
            handler_class = self._load_handler(ds_name, handler_path)
            if not handler_class:
                continue
            
            # 创建 Handler 实例
            try:
                params = ds_config.get("params", {})
                handler_instance = handler_class(schema, params)
                self._handlers[ds_name] = handler_instance
                logger.debug(f"✅ 加载 Handler: {ds_name} -> {handler_path}")
            except Exception as e:
                logger.error(f"❌ 创建 Handler 实例失败 {ds_name}: {e}")
    
    async def fetch(
        self, 
        ds_name: str, 
        context: Dict[str, Any] = None,
        save: bool = False
    ) -> Dict[str, Any]:
        """
        获取数据源数据
        
        执行指定数据源的 Handler，获取并标准化数据。
        
        Args:
            ds_name: 数据源名称
            context: 执行上下文（可选）
            save: 是否保存到数据库（暂未实现）
        
        Returns:
            标准化后的数据
        """
        if ds_name not in self._handlers:
            raise ValueError(f"数据源 {ds_name} 未找到或未启用")
        
        handler = self._handlers[ds_name]
        context = context or {}
        
        logger.info(f"🔄 开始获取数据源: {ds_name}")
        
        # 执行 Handler 的 fetch_and_normalize
        result = await handler.fetch_and_normalize(context)
        
        logger.info(f"✅ 数据源 {ds_name} 获取完成")
        
        # TODO: 如果 save=True，保存到数据库
        if save and self.data_manager:
            logger.debug(f"💾 保存数据到数据库（暂未实现）")
        
        return result
    
    def list_data_sources(self) -> List[str]:
        """列出所有可用的数据源"""
        return list(self._handlers.keys())
    
    def get_schema(self, ds_name: str):
        """获取数据源的 Schema"""
        return self._schemas.get(ds_name)
    
    async def get_stock_list(self) -> List[Dict[str, Any]]:
        """
        获取股票列表（便捷方法）
        
        Returns:
            List[Dict]: 股票列表
        """
        result = await self.fetch("stock_list")
        return result.get("data", [])
