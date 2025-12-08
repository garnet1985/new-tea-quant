from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from loguru import logger


class BaseHandler(ABC):
    """
    DataSource Handler 基类
    
    设计原则：
    1. 分离 fetch 和 normalize（职责清晰）
    2. 模板方法模式（统一流程，提供钩子）
    3. 元信息自描述（类属性）
    
    子类必须定义：
    - data_source: 数据源名称
    - renew_type: "refresh" | "incremental"
    - description: 描述
    - dependencies: 依赖的其他数据源列表
    """
    
    # ========== 类属性（子类必须定义）==========
    data_source: str = None          # 数据源名称，如 "stock_list"
    renew_type: str = None           # "refresh" 或 "incremental"
    description: str = ""            # Handler 描述
    dependencies: List[str] = []     # 依赖的其他数据源
    
    # ========== 可选的类属性 ==========
    rate_limit: Optional[int] = None          # Handler 级别的限流
    batch_size: Optional[int] = None          # 批量处理大小
    requires_date_range: bool = False         # 是否需要日期范围
    
    def __init__(self, schema, params: Dict[str, Any] = None):
        """
        初始化 Handler
        
        Args:
            schema: 数据源的 schema 定义
            params: 从 mapping.json 传入的自定义参数
        """
        self.schema = schema
        self.params = params or {}
        self._providers = {}
        
        self._validate_class_attributes()
    
    def _validate_class_attributes(self):
        """验证子类是否定义了必需的类属性"""
        if self.data_source is None:
            raise ValueError(f"{self.__class__.__name__} 必须定义 data_source")
        if self.renew_type not in ["refresh", "incremental"]:
            raise ValueError(
                f"{self.__class__.__name__} 的 renew_type 必须是 'refresh' 或 'incremental'"
            )
    
    # ========== 核心抽象方法（子类必须实现）==========
    
    @abstractmethod
    async def fetch(self, context: Dict[str, Any]) -> Any:
        """
        从数据源获取原始数据
        
        Args:
            context: 执行上下文，包含：
                - start_date: 开始日期（incremental 需要）
                - end_date: 结束日期（incremental 需要）
                - stock_codes: 股票代码列表（如果需要）
                - force_refresh: 是否强制刷新
                - ... 其他依赖数据源的数据
        
        Returns:
            原始数据（任意格式）
        """
        pass
    
    @abstractmethod
    async def normalize(self, raw_data: Any) -> Dict:
        """
        将原始数据标准化为框架 schema 格式
        
        Args:
            raw_data: fetch() 返回的原始数据
        
        Returns:
            标准化后的数据字典，格式符合 self.schema
        """
        pass
    
    # ========== 可选的钩子方法（子类可覆盖）==========
    
    async def before_fetch(self, context: Dict[str, Any]):
        """获取数据前的钩子"""
        pass
    
    async def after_fetch(self, raw_data: Any, context: Dict[str, Any]):
        """获取数据后的钩子"""
        pass
    
    async def before_normalize(self, raw_data: Any):
        """标准化前的钩子"""
        pass
    
    async def after_normalize(self, normalized_data: Dict):
        """标准化后的钩子"""
        pass
    
    async def on_error(self, error: Exception, context: Dict[str, Any]):
        """错误处理钩子"""
        logger.error(f"{self.data_source} 处理出错: {error}")
        raise
    
    # ========== 完整的执行流程（模板方法）==========
    
    async def fetch_and_normalize(self, context: Dict[str, Any]) -> Dict:
        """
        完整的数据获取和标准化流程
        
        一般情况下子类不需要覆盖此方法
        """
        try:
            await self.before_fetch(context)
            raw_data = await self.fetch(context)
            await self.after_fetch(raw_data, context)
            
            await self.before_normalize(raw_data)
            normalized_data = await self.normalize(raw_data)
            await self.after_normalize(normalized_data)
            
            if not self.validate(normalized_data):
                raise ValueError(f"数据验证失败: {self.data_source}")
            
            return normalized_data
            
        except Exception as e:
            await self.on_error(e, context)
            raise
    
    # ========== 数据验证 ==========
    
    def validate(self, data: Dict) -> bool:
        """验证数据是否符合 schema"""
        if self.schema:
            return self.schema.validate(data)
        return True
    
    # ========== Provider 管理 ==========
    
    def register_provider(self, name: str, provider):
        """注册 provider 实例"""
        self._providers[name] = provider
    
    def get_provider(self, name: str):
        """获取 provider 实例"""
        return self._providers.get(name)
    
    # ========== 元信息 ==========
    
    def get_metadata(self) -> Dict:
        """获取 Handler 元信息"""
        return {
            "data_source": self.data_source,
            "renew_type": self.renew_type,
            "description": self.description,
            "dependencies": self.dependencies,
            "rate_limit": self.rate_limit,
            "batch_size": self.batch_size,
            "requires_date_range": self.requires_date_range,
        }
    
    # ========== 辅助方法 ==========
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """获取配置参数"""
        return self.params.get(key, default)
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(data_source={self.data_source})>"
