# Data Source V2 架构设计

## 设计目标

基于 ANALYSIS.md 和 DESIGN_REVIEW.md 的分析，设计一个通用型、可扩展的数据源架构。

---

## 🎯 核心目标

1. **通用型**：支持任意数量的Provider，无需修改代码
2. **可扩展**：新增Provider只需实现接口和配置
3. **声明式**：依赖关系通过配置声明
4. **零损失**：保留所有现有功能（多线程、进度、限流等）
5. **可测试**：支持Mock Provider
6. **向后兼容**：渐进式迁移，不破坏现有功能

---

## 📐 架构设计

### 层次结构

```
┌─────────────────────────────────────────────────────────────┐
│                   应用层 (start.py)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              DataSourceManager (统一管理器)                   │
│  - 初始化Registry和Coordinator                              │
│  - 提供统一的更新入口                                         │
│  - 兼容新旧架构                                              │
└───────────┬──────────────────────────┬──────────────────────┘
            │                          │
┌───────────▼──────────┐    ┌──────────▼──────────────────────┐
│  ProviderRegistry    │◄───│    DataCoordinator              │
│  (动态挂载)           │    │    (协调器)                      │
│                      │    │  - 解析依赖                      │
│  - mount()           │    │  - 计算执行顺序                   │
│  - unmount()         │    │  - 构建上下文                     │
│  - get()             │    │  - 处理降级                      │
└───────────┬──────────┘    └────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────┐
│              BaseProvider (统一接口)                         │
│  - get_provider_info()   返回元数据                         │
│  - renew_all()           更新所有数据                        │
│  - renew_data_type()     更新指定类型                        │
│  - supports()            是否支持                            │
└─────┬────────────────────────────┬──────────────────────────┘
      │                            │
┌─────▼──────────┐        ┌────────▼─────────┐
│ TushareAdapter │        │ AKShareAdapter   │
│ (适配器)        │        │ (适配器)          │
└─────┬──────────┘        └────────┬─────────┘
      │                            │
┌─────▼──────────┐        ┌────────▼─────────┐
│ Legacy Tushare │        │ Legacy AKShare   │
│ (保留所有功能)  │        │ (保留所有功能)    │
└────────────────┘        └──────────────────┘
```

---

## 🔑 核心组件设计

### 1. BaseProvider（统一接口）

```python
# app/data_source/v2/base_provider.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    """Provider健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class Dependency:
    """依赖声明"""
    provider: str                      # 依赖的Provider名称
    data_types: List[str]              # 依赖的数据类型
    when: str = "before_renew"         # before_renew | runtime
    required: bool = True              # 是否必需
    pass_data: bool = False            # 是否需要传递数据到context

@dataclass
class ProviderInfo:
    """Provider元数据"""
    name: str                          # Provider名称
    version: str = "1.0.0"             # 版本
    provides: List[str] = None         # 提供的数据类型
    dependencies: List[Dependency] = None  # 依赖关系
    requires_auth: bool = False        # 是否需要认证

@dataclass
class ExecutionContext:
    """执行上下文"""
    end_date: str                      # 截止日期
    stock_list: List[str] = None       # 股票列表（可选）
    dependencies: Dict[str, Any] = None  # 依赖数据
    config: Dict[str, Any] = None      # 额外配置

class BaseProvider(ABC):
    """
    Provider 基类（统一接口）
    
    所有数据源Provider必须实现此接口
    """
    
    def __init__(self, data_manager, is_verbose: bool = False):
        """
        初始化Provider
        
        Args:
            data_manager: DataManager实例（访问数据库和DataService）
            is_verbose: 是否详细日志
        """
        self.data_manager = data_manager
        self.is_verbose = is_verbose
    
    # ===== 必须实现的方法 =====
    
    @abstractmethod
    def get_provider_info(self) -> ProviderInfo:
        """
        返回Provider元数据
        
        用于：
        - 依赖解析
        - 路由决策
        - 文档生成
        """
        pass
    
    @abstractmethod
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """
        更新此Provider提供的所有数据类型
        
        Args:
            end_date: 截止日期（YYYYMMDD）
            context: 执行上下文（包含依赖数据等）
        """
        pass
    
    @abstractmethod
    def supports_data_type(self, data_type: str) -> bool:
        """
        是否支持某种数据类型
        
        Args:
            data_type: 数据类型名称
        
        Returns:
            bool: 是否支持
        """
        pass
    
    # ===== 可选实现的方法 =====
    
    async def renew_data_type(
        self, 
        data_type: str, 
        end_date: str, 
        context: ExecutionContext = None
    ):
        """
        更新指定数据类型（可选）
        
        如果不实现，默认调用 renew_all()
        
        Args:
            data_type: 数据类型名称
            end_date: 截止日期
            context: 执行上下文
        """
        return await self.renew_all(end_date, context)
    
    def get_health_status(self) -> HealthStatus:
        """
        返回健康状态（可选）
        
        用于监控和降级决策
        """
        return HealthStatus.HEALTHY
    
    def validate_dependencies(self, context: ExecutionContext) -> bool:
        """
        验证依赖是否满足（可选）
        
        Args:
            context: 执行上下文
        
        Returns:
            bool: 依赖是否满足
        """
        info = self.get_provider_info()
        
        for dep in info.dependencies:
            if dep.required and dep.pass_data:
                # 检查context中是否有所需的依赖数据
                for data_type in dep.data_types:
                    if data_type not in (context.dependencies or {}):
                        return False
        
        return True
```

---

### 2. ProviderRegistry（动态挂载）

```python
# app/data_source/v2/provider_registry.py

from typing import Dict, List, Optional
from loguru import logger
from .base_provider import BaseProvider, ProviderMetadata

class ProviderRegistry:
    """
    Provider 注册表
    
    职责：
    1. 动态挂载/卸载Provider
    2. 管理Provider生命周期
    3. 构建数据类型索引
    4. 提供查询接口
    """
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._metadata: Dict[str, ProviderMetadata] = {}
        self._data_type_index: Dict[str, List[str]] = {}
    
    def mount(self, name: str, provider: BaseProvider, metadata: ProviderMetadata = None):
        """
        挂载Provider
        
        Args:
            name: Provider名称（如 'tushare'）
            provider: Provider实例
            metadata: Provider元数据（可选，如果不提供则从provider获取）
        """
        # 验证
        if not isinstance(provider, BaseProvider):
            raise TypeError(f"Provider must implement BaseProvider interface")
        
        # 获取元数据
        if not metadata:
            info = provider.get_provider_info()
            metadata = ProviderMetadata(
                name=info.name,
                provides=info.provides or [],
                dependencies=info.dependencies or []
            )
        
        # 注册
        self._providers[name] = provider
        self._metadata[name] = metadata
        
        # 更新索引
        for data_type in metadata.provides:
            if data_type not in self._data_type_index:
                self._data_type_index[data_type] = []
            if name not in self._data_type_index[data_type]:
                self._data_type_index[data_type].append(name)
        
        logger.info(f"✅ Provider '{name}' 已挂载，提供: {metadata.provides}")
    
    def unmount(self, name: str):
        """卸载Provider"""
        if name not in self._providers:
            logger.warning(f"Provider '{name}' 未挂载")
            return
        
        # 清理索引
        metadata = self._metadata[name]
        for data_type in metadata.provides:
            if data_type in self._data_type_index:
                self._data_type_index[data_type].remove(name)
        
        # 删除
        del self._providers[name]
        del self._metadata[name]
        logger.info(f"Provider '{name}' 已卸载")
    
    def get(self, name: str) -> Optional[BaseProvider]:
        """获取Provider实例"""
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """列出所有已挂载的Provider"""
        return list(self._providers.keys())
    
    def get_providers_for(self, data_type: str, enabled_only: bool = True) -> List[str]:
        """
        获取支持某数据类型的所有Provider
        
        Args:
            data_type: 数据类型
            enabled_only: 是否只返回启用的Provider
        
        Returns:
            Provider名称列表
        """
        providers = self._data_type_index.get(data_type, [])
        
        if enabled_only:
            # 过滤禁用的Provider
            providers = [p for p in providers if self._metadata[p].enabled]
        
        return providers
    
    def get_metadata(self, name: str) -> Optional[ProviderMetadata]:
        """获取Provider元数据"""
        return self._metadata.get(name)
    
    def has_provider(self, name: str) -> bool:
        """是否存在某个Provider"""
        return name in self._providers
```

---

### 3. DataCoordinator（协调器）⭐ 核心

```python
# app/data_source/v2/data_coordinator.py

from typing import List, Dict, Any, Optional
from loguru import logger
from .provider_registry import ProviderRegistry
from .base_provider import ExecutionContext, Dependency

class DependencyGraph:
    """依赖图（用于拓扑排序）"""
    
    def __init__(self):
        self.nodes = {}  # {name: metadata}
        self.edges = {}  # {from: [to, ...]}
    
    def add_node(self, name: str, metadata):
        """添加节点"""
        self.nodes[name] = metadata
        if name not in self.edges:
            self.edges[name] = []
    
    def add_edge(self, from_node: str, to_node: str):
        """添加边（依赖关系）"""
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append(to_node)
    
    def topological_sort(self) -> List[str]:
        """
        拓扑排序（计算执行顺序）
        
        Returns:
            Provider名称列表，按依赖顺序排列
        
        Raises:
            ValueError: 如果存在循环依赖
        """
        # Kahn算法
        in_degree = {node: 0 for node in self.nodes}
        
        for from_node, to_nodes in self.edges.items():
            for to_node in to_nodes:
                in_degree[to_node] += 1
        
        # 入度为0的节点
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self.edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查循环依赖
        if len(result) != len(self.nodes):
            raise ValueError("检测到循环依赖")
        
        return result


class DataCoordinator:
    """
    数据协调器
    
    职责：
    1. 解析依赖关系，构建依赖图
    2. 计算执行顺序（拓扑排序）
    3. 确保依赖满足后再执行
    4. 构建执行上下文（传递依赖数据）
    5. 处理失败和降级
    """
    
    def __init__(self, registry: ProviderRegistry, data_manager):
        self.registry = registry
        self.data_manager = data_manager
        self._dependency_graph = None
        self._execution_order = None
    
    def build_dependency_graph(self) -> DependencyGraph:
        """
        构建依赖图
        
        Returns:
            DependencyGraph: 依赖图
        """
        graph = DependencyGraph()
        
        # 添加所有Provider节点
        for provider_name in self.registry.list_providers():
            metadata = self.registry.get_metadata(provider_name)
            graph.add_node(provider_name, metadata)
        
        # 添加依赖边
        for provider_name in self.registry.list_providers():
            metadata = self.registry.get_metadata(provider_name)
            
            for dep in metadata.dependencies:
                # from依赖Provider → to当前Provider
                graph.add_edge(dep.provider, provider_name)
        
        return graph
    
    def resolve_execution_order(self) -> List[str]:
        """
        计算执行顺序（拓扑排序）
        
        Returns:
            Provider名称列表，按依赖顺序排列
        """
        if not self._execution_order:
            self._dependency_graph = self.build_dependency_graph()
            self._execution_order = self._dependency_graph.topological_sort()
            
            logger.info(f"📋 Provider执行顺序: {' → '.join(self._execution_order)}")
        
        return self._execution_order
    
    async def renew_all_providers(self, end_date: str):
        """
        更新所有Provider（按依赖顺序）
        
        Args:
            end_date: 截止日期（YYYYMMDD）
        """
        order = self.resolve_execution_order()
        
        logger.info(f"🔄 开始更新所有Provider，截止日期: {end_date}")
        
        for provider_name in order:
            provider = self.registry.get(provider_name)
            
            if not provider:
                logger.warning(f"⚠️  Provider '{provider_name}' 未找到，跳过")
                continue
            
            # 构建执行上下文
            context = await self._build_context(provider_name, end_date)
            
            # 执行更新
            try:
                logger.info(f"▶️  更新 {provider_name}...")
                await provider.renew_all(end_date, context)
                logger.info(f"✅ {provider_name} 更新完成")
            except Exception as e:
                logger.error(f"❌ {provider_name} 更新失败: {e}")
                # 根据配置决定是否继续
                # TODO: 添加 stop_on_error 配置
    
    async def coordinate_update(self, data_type: str, end_date: str):
        """
        协调某个数据类型的更新
        
        自动处理依赖：
        1. 找到负责此数据类型的Provider
        2. 检查依赖是否满足
        3. 递归更新依赖（如果不满足）
        4. 构建执行上下文
        5. 执行更新
        
        Args:
            data_type: 数据类型（如 'stock_kline'）
            end_date: 截止日期
        """
        # 1. 找到负责的Provider
        providers = self.registry.get_providers_for(data_type)
        if not providers:
            logger.error(f"❌ 没有Provider支持数据类型: {data_type}")
            return
        
        provider_name = providers[0]  # 使用第一个（主Provider）
        provider = self.registry.get(provider_name)
        
        # 2. 获取依赖
        metadata = self.registry.get_metadata(provider_name)
        
        # 3. 确保依赖满足
        for dep in metadata.dependencies:
            if dep.when == "before_renew":
                for dep_data_type in dep.data_types:
                    # 检查依赖数据是否可用
                    if not await self._is_data_available(dep_data_type, end_date):
                        logger.info(f"🔗 依赖数据 {dep_data_type} 不可用，先更新...")
                        # 递归更新依赖
                        await self.coordinate_update(dep_data_type, end_date)
        
        # 4. 构建执行上下文
        context = await self._build_context(provider_name, end_date)
        
        # 5. 执行更新
        try:
            await provider.renew_data_type(data_type, end_date, context)
        except Exception as e:
            # 6. 失败处理
            await self._handle_failure(data_type, provider_name, e)
    
    async def _build_context(self, provider_name: str, end_date: str) -> ExecutionContext:
        """
        构建执行上下文
        
        Args:
            provider_name: Provider名称
            end_date: 截止日期
        
        Returns:
            ExecutionContext: 执行上下文
        """
        metadata = self.registry.get_metadata(provider_name)
        context = ExecutionContext(end_date=end_date)
        
        # 添加依赖数据
        dependencies_data = {}
        for dep in metadata.dependencies:
            if dep.pass_data:
                # 从数据库或其他Provider获取依赖数据
                for data_type in dep.data_types:
                    data = await self._fetch_dependency_data(data_type, end_date)
                    if data:
                        dependencies_data[data_type] = data
        
        context.dependencies = dependencies_data
        
        # 特殊处理：stock_list
        if any('stock_list' in dep.data_types for dep in metadata.dependencies):
            # 从Tushare获取股票列表
            stock_list = await self._fetch_stock_list()
            context.stock_list = stock_list
        
        return context
    
    async def _is_data_available(self, data_type: str, end_date: str) -> bool:
        """
        检查数据是否可用（在数据库中）
        
        Args:
            data_type: 数据类型
            end_date: 截止日期
        
        Returns:
            bool: 数据是否可用
        """
        # TODO: 根据data_type映射到table_name
        # TODO: 查询数据库最新记录
        # TODO: 检查是否已更新到end_date
        
        # 简化实现：检查表是否有数据
        from app.data_source.config import DATA_TYPE_TABLE_MAPPING
        table_name = DATA_TYPE_TABLE_MAPPING.get(data_type)
        
        if not table_name:
            return False
        
        model = self.data_manager.get_model(table_name)
        latest = model.load_latest_records()
        
        return len(latest) > 0
    
    async def _fetch_dependency_data(self, data_type: str, end_date: str) -> Any:
        """
        获取依赖数据
        
        Args:
            data_type: 数据类型
            end_date: 截止日期
        
        Returns:
            依赖数据
        """
        # 从DataManager获取数据
        # TODO: 根据data_type选择合适的DataService
        pass
    
    async def _fetch_stock_list(self) -> List[str]:
        """获取股票列表"""
        # 使用DataManager的接口
        stock_service = self.data_manager.get_data_service('stock_related.stock')
        if stock_service:
            stocks = stock_service.load_stock_list()
            return [s['ts_code'] for s in stocks]
        return []
    
    async def _handle_failure(self, data_type: str, provider_name: str, error: Exception):
        """
        处理失败
        
        Args:
            data_type: 数据类型
            provider_name: 失败的Provider
            error: 错误
        """
        logger.error(f"❌ {provider_name} 更新 {data_type} 失败: {error}")
        
        # TODO: 实现降级策略
        # 1. 检查是否有备用Provider
        # 2. 尝试备用Provider
        # 3. 如果所有Provider都失败，使用缓存或报错
        
        raise error
```

---

### 4. TushareAdapter（适配器示例）

```python
# app/data_source/v2/adapters/tushare_adapter.py

from app.data_source.v2.base_provider import BaseProvider, ProviderInfo, ExecutionContext
from app.data_source.providers.tushare.main import Tushare as LegacyTushare

class TushareAdapter(BaseProvider):
    """
    Tushare 适配器
    
    职责：
    1. 包装Legacy Tushare
    2. 提供统一接口
    3. 保留所有现有功能
    """
    
    def __init__(self, data_manager, is_verbose: bool = False):
        super().__init__(data_manager, is_verbose)
        
        # 创建Legacy实例（保留所有功能）
        self._legacy = LegacyTushare(
            connected_db=data_manager.db,
            is_verbose=is_verbose
        )
    
    def get_provider_info(self) -> ProviderInfo:
        """返回Provider元数据"""
        return ProviderInfo(
            name="tushare",
            version="1.0.0",
            provides=[
                "stock_list",
                "stock_kline",
                "corporate_finance",
                "gdp",
                "price_indexes",  # CPI, PPI, PMI
                "shibor",
                "lpr",
                "stock_index_indicator",
                "stock_index_indicator_weight",
                "industry_capital_flow"
            ],
            dependencies=[],  # Tushare无依赖
            requires_auth=True
        )
    
    def supports_data_type(self, data_type: str) -> bool:
        """是否支持某种数据类型"""
        info = self.get_provider_info()
        return data_type in info.provides
    
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """
        更新所有数据（委托给Legacy）
        
        保留所有现有功能：
        - 多线程
        - 进度跟踪
        - 限流器
        - 错误重试
        """
        stock_list = context.stock_list if context else None
        
        # 直接调用Legacy实现
        return await self._legacy.renew(end_date, stock_list)
    
    async def renew_data_type(self, data_type: str, end_date: str, context: ExecutionContext = None):
        """
        更新指定数据类型
        
        映射到对应的Renewer
        """
        stock_list = context.stock_list if context else None
        
        # 映射到具体的Renewer
        renewer_map = {
            'stock_list': self._legacy.stock_list_renewer,
            'stock_kline': self._legacy.stock_kline_renewer,
            'corporate_finance': self._legacy.corporate_finance_renewer,
            'gdp': self._legacy.gdp_renewer,
            'price_indexes': self._legacy.price_indexes_renewer,
            'shibor': self._legacy.shibor_renewer,
            'lpr': self._legacy.lpr_renewer,
            'stock_index_indicator': self._legacy.stock_index_indicator_renewer,
            'stock_index_indicator_weight': self._legacy.stock_index_indicator_weight_renewer,
            'industry_capital_flow': self._legacy.industry_capital_flow_renewer,
        }
        
        renewer = renewer_map.get(data_type)
        if not renewer:
            raise ValueError(f"不支持的数据类型: {data_type}")
        
        # 调用对应的Renewer
        return renewer.renew(end_date, stock_list)
    
    def get_latest_market_open_day(self):
        """获取最新交易日（特有方法）"""
        return self._legacy.get_latest_market_open_day()
    
    def load_filtered_stock_list(self):
        """加载过滤后的股票列表（特有方法）"""
        return self._legacy.load_filtered_stock_list()
```

---

### 5. AKShareAdapter（适配器示例）

```python
# app/data_source/v2/adapters/akshare_adapter.py

from app.data_source.v2.base_provider import BaseProvider, ProviderInfo, ExecutionContext, Dependency
from app.data_source.providers.akshare.main import AKShare as LegacyAKShare

class AKShareAdapter(BaseProvider):
    """
    AKShare 适配器
    
    特点：依赖Tushare的K线数据
    """
    
    def __init__(self, data_manager, is_verbose: bool = False):
        super().__init__(data_manager, is_verbose)
        
        # 创建Legacy实例
        self._legacy = LegacyAKShare(
            connected_db=data_manager.db,
            is_verbose=is_verbose
        )
    
    def get_provider_info(self) -> ProviderInfo:
        """返回Provider元数据"""
        return ProviderInfo(
            name="akshare",
            version="1.0.0",
            provides=["adj_factor"],  # 只提供复权因子
            dependencies=[
                Dependency(
                    provider="tushare",
                    data_types=["stock_kline"],  # 依赖K线数据
                    when="before_renew",
                    required=True,
                    pass_data=False  # 不需要传递数据，只需要确保存在
                )
            ],
            requires_auth=False
        )
    
    def supports_data_type(self, data_type: str) -> bool:
        """是否支持某种数据类型"""
        return data_type == "adj_factor"
    
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """
        更新复权因子
        
        注意：需要先有K线数据（由Coordinator确保）
        """
        # 验证依赖
        if not self.validate_dependencies(context):
            raise ValueError("依赖不满足：需要先有K线数据")
        
        stock_list = context.stock_list if context else None
        
        # 注入Tushare依赖（Legacy需要）
        # TODO: 这是过渡期方案，未来应该通过context传递
        tushare_adapter = self.registry.get('tushare')
        if tushare_adapter:
            self._legacy.inject_dependency(tushare_adapter._legacy)
        
        # 调用Legacy实现
        return await self._legacy.renew(end_date, stock_list)
```

---

## 🚀 如何支持新Provider？

### 场景：新增 Wind Provider

#### 步骤1：实现接口

```python
# app/data_source/providers/wind/wind_provider.py

class WindProvider(BaseProvider):
    """Wind 数据Provider"""
    
    def get_provider_info(self):
        return ProviderInfo(
            name="wind",
            version="1.0.0",
            provides=["financial_news", "analyst_rating"],
            dependencies=[
                Dependency(
                    provider="tushare",
                    data_types=["stock_list"],
                    when="before_renew",
                    required=True,
                    pass_data=True  # 需要传递股票列表
                )
            ],
            requires_auth=True
        )
    
    def supports_data_type(self, data_type: str) -> bool:
        return data_type in ["financial_news", "analyst_rating"]
    
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """更新所有数据"""
        # 从context获取股票列表
        stock_list = context.stock_list if context else []
        
        # 更新财经新闻
        await self._renew_financial_news(end_date, stock_list)
        
        # 更新分析师评级
        await self._renew_analyst_rating(end_date, stock_list)
```

#### 步骤2：注册Provider

```python
# app/data_source/data_source_manager.py

def _init_v2(self):
    # 挂载Tushare
    self.registry.mount('tushare', TushareAdapter(self.data_manager))
    
    # 挂载AKShare
    self.registry.mount('akshare', AKShareAdapter(self.data_manager))
    
    # ✨ 挂载Wind（只需这一行）
    self.registry.mount('wind', WindProvider(self.data_manager))
    
    # 创建协调器
    self.coordinator = DataCoordinator(self.registry, self.data_manager)
    
    # 自动计算执行顺序
    # 结果: [tushare, akshare, wind]
```

#### 步骤3：配置（可选）

```yaml
# config/data_source.yaml

providers:
  wind:
    enabled: true
    class: "app.data_source.providers.wind.WindProvider"
    auth:
      username: ${WIND_USER}
      password: ${WIND_PASS}
    rate_limits:
      default: 100

data_types:
  financial_news:
    provider: wind
    table: financial_news
    renew_mode: incremental
```

#### 完成！

**无需修改任何现有代码**：
- ✅ DataCoordinator 自动解析依赖
- ✅ 执行顺序自动计算
- ✅ stock_list 自动传递
- ✅ 失败自动处理

---

## 🎯 关键改进对比

| 功能 | 现有架构 | 新架构 | 改进效果 |
|-----|---------|--------|---------|
| **依赖管理** | 硬编码 | 声明式 | 🟢🟢🟢🟢🟢 |
| **新增Provider** | 修改代码 | 只需配置 | 🟢🟢🟢🟢🟢 |
| **执行顺序** | 手动编排 | 自动计算 | 🟢🟢🟢🟢 |
| **接口一致性** | 不一致 | 统一 | 🟢🟢🟢🟢🟢 |
| **测试性** | 困难 | 易于Mock | 🟢🟢🟢🟢 |
| **降级策略** | 无 | 支持 | 🟢🟢🟢 |
| **多线程** | 保留 | 保留 | 🟢（不变）|
| **进度跟踪** | 保留 | 保留 | 🟢（不变）|
| **限流器** | 保留 | 保留 | 🟢（不变）|

---

## 📋 实施建议

### Phase 1：核心组件（3-4天）
1. 实现 `BaseProvider` 接口
2. 实现 `ProviderRegistry`
3. 实现 `DataCoordinator`
4. 编写单元测试

### Phase 2：适配器（2-3天）
1. 实现 `TushareAdapter`
2. 实现 `AKShareAdapter`
3. 集成测试（对比新旧输出）

### Phase 3：配置化（1-2天）
1. 设计配置格式（YAML）
2. 实现配置加载
3. 支持可选切换

### Phase 4：降级和监控（可选）
1. 实现降级策略
2. 实现健康检查
3. 添加监控指标

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

