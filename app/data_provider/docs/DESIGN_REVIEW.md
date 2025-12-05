# Data Source 设计评审与改进方向

## 目的

基于 ANALYSIS.md 的功能梳理，评审现有设计的优缺点，提出通用型架构的改进方向。

---

## ✅ 现有设计的优点

### 1. 配置驱动 ⭐⭐⭐⭐⭐
```python
# 每个Renewer独立配置
CONFIG = {
    'table_name': 'stock_kline',
    'renew_mode': 'incremental',
    'job_mode': 'multithread',
    'apis': [...],
    'date': {...},
    'multithread': {...}
}
```

**优点：**
- 声明式配置，清晰易懂
- 新增数据类型只需添加配置
- 配置与逻辑分离

**保留建议：** ✅ 完全保留，这是核心优势

---

### 2. BaseRenewer 抽象 ⭐⭐⭐⭐
```python
# 提供默认实现，子类按需重写
class BaseRenewer:
    def renew()              # 主流程（不重写）
    def build_jobs()         # 可重写
    def prepare_data()       # ⭐ 最常重写
    def save_data()          # 可重写
```

**优点：**
- 模板方法模式（Template Method）
- 默认实现覆盖90%场景
- 子类只需关注特殊逻辑
- 代码复用率高

**保留建议：** ✅ 保留核心思想，但需要改进

---

### 3. 增量更新智能判断 ⭐⭐⭐⭐⭐
```python
# 自动计算需要更新的范围
- 查询DB最新记录
- 计算下一个周期
- 处理披露延迟
- 构建增量任务
```

**优点：**
- 节省带宽和时间
- 自动化程度高
- 支持中断恢复

**保留建议：** ✅ 完全保留

---

### 4. 多线程 + 限流 ⭐⭐⭐⭐
```python
# 智能buffer机制
buffer = workers + 5  # 多线程缓冲

# 线程安全
- 线程局部DB
- 进度计数器加锁
- 限流器线程安全
```

**优点：**
- 性能优秀
- 线程安全
- buffer设计巧妙

**保留建议：** ✅ 完全保留，但需要提取为通用组件

---

### 5. 字段映射灵活 ⭐⭐⭐
```python
mapping:
    - 简单映射: "api_field"
    - 转换函数: {source: "x", transform: lambda x: x * 100}
    - 默认值: {source: "x", default: 0}
    - 常量值: {value: "constant"}
```

**优点：**
- 支持多种映射方式
- 声明式配置
- 易于理解

**保留建议：** ✅ 保留，但可简化为常用的3种

---

## ❌ 现有设计的缺点

### 1. 依赖关系硬编码 ⭐⭐⭐⭐⭐ 最严重

#### 问题现状
```python
# DataSourceManager.renew_data()
async def renew_data(self, latest_market_open_day: str):
    tu = self.sources['tushare']
    
    # 1. 更新股票列表
    tu.stock_list_renewer.renew(latest_market_open_day)
    
    # 2. 加载股票列表
    latest_stock_list = tu.load_filtered_stock_list()
    
    # 3. 更新 Tushare
    await tu.renew(latest_market_open_day, latest_stock_list)
    
    # 4. 更新 AKShare（硬编码依赖）
    ak = self.sources['akshare']
    ak.inject_dependency(tu)  # ⚠️ 硬编码注入
    await ak.renew(latest_market_open_day, latest_stock_list)
```

#### 为什么这是问题？
1. **不可扩展**：新增Provider需要修改 `renew_data()`
2. **依赖不透明**：`inject_dependency` 是什么？不看代码不知道
3. **顺序固定**：Tushare必须在AKShare前，写死在代码里
4. **测试困难**：无法单独测试AKShare（依赖Tushare）

#### 如果新增Provider会怎样？
```python
# 场景：新增 Wind（依赖Tushare的股票列表）
wind = Wind(self.db)
wind.inject_dependency(tu)  # 又是硬编码
await wind.renew(latest_market_open_day, latest_stock_list)

# 场景：新增 Choice（依赖Wind和AKShare）
choice = Choice(self.db)
choice.inject_dependency_wind(wind)      # 方法名都不一样
choice.inject_dependency_akshare(ak)     # 混乱
await choice.renew(...)

# 问题：依赖关系越来越复杂，代码越来越乱
```

#### 改进方向 🎯
```yaml
# 配置化依赖关系
providers:
  tushare:
    provides: [stock_list, stock_kline, macro_economy]
    dependencies: []
  
  akshare:
    provides: [adj_factor]
    dependencies:
      - provider: tushare
        data_types: [stock_kline]
        when: before_renew  # 更新前需要
  
  wind:
    provides: [financial_news]
    dependencies:
      - provider: tushare
        data_types: [stock_list]
  
  choice:
    provides: [analyst_rating]
    dependencies:
      - provider: wind
        data_types: [financial_news]
      - provider: akshare
        data_types: [adj_factor]
```

#### 配置化后的好处
```python
# DataCoordinator 自动解析依赖
coordinator = DataCoordinator(registry, config)

# 自动计算执行顺序
order = coordinator.resolve_execution_order()
# 结果: [tushare, akshare, wind, choice]

# 自动传递依赖数据
for provider_name in order:
    provider = registry.get(provider_name)
    deps = coordinator.resolve_dependencies(provider_name)
    await provider.renew(end_date, dependencies=deps)
```

---

### 2. Provider 接口不统一 ⭐⭐⭐⭐

#### 问题现状
```python
# Tushare
class Tushare:
    async def renew(self, latest_market_open_day: str, stock_list: list):
        pass
    
    def load_filtered_stock_list(self):  # 特有方法
        pass
    
    async def get_latest_market_open_day(self):  # 特有方法
        pass

# AKShare
class AKShare:
    async def renew(self, latest_market_open_day: str = None, stock_list: list = None):
        pass
    
    def inject_dependency(self, tu: Tushare):  # 特有方法
        pass
```

#### 为什么这是问题？
1. **方法签名不一致**：`renew()` 参数不同
2. **特有方法太多**：每个Provider都有自己的方法
3. **无法通用化**：`DataSourceManager` 无法统一处理
4. **测试复杂**：每个Provider需要不同的测试方式

#### 改进方向 🎯
```python
# 统一接口
class BaseProvider(ABC):
    """所有Provider必须实现的接口"""
    
    @abstractmethod
    async def renew_all(self, end_date: str, context: Dict = None):
        """统一的更新入口"""
        pass
    
    @abstractmethod
    def supports_data_type(self, data_type: str) -> bool:
        """是否支持某种数据类型"""
        pass
    
    @abstractmethod
    def get_provided_data_types(self) -> List[str]:
        """返回此Provider提供的数据类型"""
        pass
    
    @abstractmethod
    def get_dependencies(self) -> List[Dependency]:
        """返回此Provider的依赖"""
        pass
    
    # 可选：扩展方法
    def fetch(self, request: DataRequest) -> DataResponse:
        """按需获取数据（可选）"""
        pass
```

#### 统一后的好处
```python
# DataCoordinator 可以通用处理
class DataCoordinator:
    async def renew_all_providers(self, end_date: str):
        order = self._resolve_execution_order()
        
        for provider_name in order:
            provider = self.registry.get(provider_name)
            
            # 统一的接口调用
            context = self._build_context(provider)
            await provider.renew_all(end_date, context)
```

---

### 3. 缺乏数据协调层 ⭐⭐⭐⭐⭐

#### 问题现状
```python
# 复权因子依赖K线数据，但协调逻辑分散
# 在 DataSourceManager 中：
await tu.renew(...)  # 更新K线
ak.inject_dependency(tu)  # 手动注入
await ak.renew(...)  # 更新复权因子

# 问题：
# 1. 如果K线更新失败怎么办？
# 2. 如果只想更新复权因子怎么办？
# 3. 如何知道K线是否已更新？
```

#### 改进方向 🎯
```python
class DataCoordinator:
    """数据协调层：处理复杂依赖和协同"""
    
    async def coordinate_update(self, data_type: str, end_date: str):
        """协调某个数据类型的更新"""
        
        # 1. 检查依赖
        deps = self._get_dependencies(data_type)
        
        # 2. 递归确保依赖已满足
        for dep in deps:
            if not self._is_data_available(dep):
                await self.coordinate_update(dep.data_type, end_date)
        
        # 3. 执行更新
        provider = self._get_provider_for(data_type)
        context = self._build_context(provider, deps)
        await provider.renew_data_type(data_type, end_date, context)
    
    def _is_data_available(self, dep: Dependency) -> bool:
        """检查依赖数据是否可用"""
        # 查询数据库或缓存
        pass
    
    def _build_context(self, provider, deps) -> Dict:
        """构建执行上下文（包含依赖数据）"""
        context = {}
        for dep in deps:
            if dep.pass_data:
                # 从DB或其他Provider获取依赖数据
                context[dep.name] = self._fetch_dependency_data(dep)
        return context
```

#### 协调层的好处
```python
# 用户只需要请求想要的数据
coordinator.coordinate_update('adj_factor', '20250101')

# 协调层自动：
# 1. 检查是否有K线数据
# 2. 如果没有，先更新K线
# 3. 然后更新复权因子
# 4. 处理失败和回滚
```

---

### 4. 配置格式不统一 ⭐⭐⭐

#### 问题现状
```python
# Renewer配置：Python字典
CONFIG = {
    'table_name': 'stock_kline',
    'apis': [...]
}

# Tushare配置：单独的配置类
class TushareConfig:
    kline_rate_limit = RateLimitConfig(...)

# DataSourceManager：硬编码
self.sources = {
    'tushare': Tushare(...),
    'akshare': AKShare(...),
}
```

#### 改进方向 🎯
```yaml
# 统一的配置文件：config/data_source.yaml

providers:
  tushare:
    enabled: true
    class: "app.data_source.providers.tushare.TushareProvider"
    auth:
      token_file: "auth/token.txt"
    rate_limits:
      default: 200
      kline: 500
    
  akshare:
    enabled: true
    class: "app.data_source.providers.akshare.AKShareProvider"
    rate_limits:
      default: 1000

data_types:
  stock_kline:
    provider: tushare
    table: stock_kline
    renew_mode: incremental
    job_mode: multithread
    workers: 4
  
  adj_factor:
    provider: akshare
    table: adj_factor
    renew_mode: incremental
    dependencies:
      - data_type: stock_kline
        provider: tushare
```

---

### 5. 缺乏降级策略 ⭐⭐⭐

#### 问题现状
```python
# 如果Tushare挂了，整个系统停止
# 没有备用Provider
# 没有缓存策略
```

#### 改进方向 🎯
```yaml
data_types:
  stock_kline:
    providers:
      - name: tushare
        priority: 1
      - name: akshare
        priority: 2  # 备用
      - name: local_cache
        priority: 3  # 最后的备用
    
    fallback_strategy: cascade  # 级联降级
```

---

### 6. 测试困难 ⭐⭐⭐⭐

#### 问题现状
```python
# 1. 依赖真实API
# 2. 依赖真实数据库
# 3. 依赖其他Provider
# 4. 无法独立测试
```

#### 改进方向 🎯
```python
# Mock Provider
class MockTushareProvider(BaseProvider):
    def __init__(self, mock_data: Dict):
        self.mock_data = mock_data
    
    async def renew_all(self, end_date, context):
        return self.mock_data

# 测试
def test_akshare_depends_on_tushare():
    # 注册Mock
    registry = ProviderRegistry()
    registry.mount('tushare', MockTushareProvider({
        'stock_kline': [...]
    }))
    registry.mount('akshare', AKShareProvider(...))
    
    # 测试协调
    coordinator = DataCoordinator(registry)
    result = await coordinator.coordinate_update('adj_factor', '20250101')
    
    assert result.success
```

---

## 🎯 通用型架构改进方向

### 核心目标

1. **可扩展**：新增Provider只需配置，无需修改代码
2. **可插拔**：Provider可以动态挂载/卸载
3. **声明式**：依赖关系通过配置声明
4. **可测试**：支持Mock Provider
5. **容错性**：支持降级策略

---

### 改进方案 1：统一接口（BaseProvider）

```python
class BaseProvider(ABC):
    """Provider 统一接口"""
    
    # ===== 必须实现 =====
    
    @abstractmethod
    def get_provider_info(self) -> ProviderInfo:
        """
        返回Provider信息
        
        Returns:
            ProviderInfo:
                name: "tushare"
                version: "1.0.0"
                provides: ["stock_list", "stock_kline", ...]
                requires: []  # 需要的外部依赖（API key等）
        """
        pass
    
    @abstractmethod
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """
        更新所有数据类型
        
        Args:
            end_date: 截止日期
            context: 执行上下文（包含依赖数据、配置等）
        """
        pass
    
    @abstractmethod
    def supports_data_type(self, data_type: str) -> bool:
        """是否支持某种数据类型"""
        pass
    
    # ===== 可选实现 =====
    
    async def renew_data_type(self, data_type: str, end_date: str, context: ExecutionContext = None):
        """
        更新指定数据类型（可选）
        
        如果不实现，默认调用 renew_all()
        """
        return await self.renew_all(end_date, context)
    
    def fetch(self, request: DataRequest) -> DataResponse:
        """
        按需获取数据（可选）
        
        用于DataService层的即时查询
        """
        raise NotImplementedError("This provider does not support fetch")
    
    def get_health_status(self) -> HealthStatus:
        """
        返回健康状态（可选）
        
        用于监控和降级决策
        """
        return HealthStatus.HEALTHY
```

**优点：**
- 统一的方法签名
- 强制实现必要方法
- 可选方法保持灵活性
- 易于Mock和测试

---

### 改进方案 2：依赖声明（ProviderMetadata）

```python
@dataclass
class Dependency:
    """依赖声明"""
    provider: str               # 依赖的Provider
    data_types: List[str]       # 依赖的数据类型
    when: str = "before_renew"  # before_renew | runtime
    required: bool = True       # 是否必需
    pass_data: bool = False     # 是否传递数据

@dataclass
class ProviderMetadata:
    """Provider元数据（通过配置或代码声明）"""
    name: str
    provides: List[str]         # 提供的数据类型
    dependencies: List[Dependency]  # 依赖关系
    priority: int = 1           # 优先级
    enabled: bool = True

# 使用方式1：代码声明
class TushareAdapter(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="tushare",
            provides=["stock_list", "stock_kline", "macro_economy"],
            dependencies=[]
        )

# 使用方式2：配置声明
# config/providers.yaml
providers:
  akshare:
    provides: [adj_factor]
    dependencies:
      - provider: tushare
        data_types: [stock_kline]
        when: before_renew
        required: true
```

**优点：**
- 依赖关系显式声明
- 支持代码和配置两种方式
- 易于理解和维护
- 自动生成依赖图

---

### 改进方案 3：数据协调器（DataCoordinator）

```python
class DataCoordinator:
    """
    数据协调器：处理Provider之间的依赖和协同
    
    职责：
    1. 解析依赖关系，计算执行顺序
    2. 确保依赖满足后再执行
    3. 处理失败和降级
    4. 提供执行上下文
    """
    
    def __init__(self, registry: ProviderRegistry, config: Dict):
        self.registry = registry
        self.config = config
        self._dependency_graph = self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> DependencyGraph:
        """构建依赖图"""
        graph = DependencyGraph()
        
        for provider_name in self.registry.list_providers():
            provider = self.registry.get(provider_name)
            info = provider.get_provider_info()
            
            # 添加节点
            graph.add_node(provider_name, info)
            
            # 添加边（依赖关系）
            for dep in info.dependencies:
                graph.add_edge(dep.provider, provider_name, dep)
        
        return graph
    
    def resolve_execution_order(self) -> List[str]:
        """
        计算执行顺序（拓扑排序）
        
        Returns:
            Provider名称列表，按依赖顺序排列
        
        Raises:
            CircularDependencyError: 如果存在循环依赖
        """
        return self._dependency_graph.topological_sort()
    
    async def coordinate_update(self, data_type: str, end_date: str):
        """
        协调某个数据类型的更新
        
        自动处理依赖：
        1. 检查依赖是否满足
        2. 如果不满足，递归更新依赖
        3. 构建执行上下文
        4. 执行更新
        """
        # 1. 找到负责此数据类型的Provider
        provider_name = self._get_provider_for(data_type)
        provider = self.registry.get(provider_name)
        
        # 2. 获取依赖
        info = provider.get_provider_info()
        deps = [d for d in info.dependencies if data_type in d.affected_types]
        
        # 3. 确保依赖满足
        for dep in deps:
            if dep.when == "before_renew":
                for dep_data_type in dep.data_types:
                    if not await self._is_data_available(dep_data_type, end_date):
                        # 递归更新依赖
                        await self.coordinate_update(dep_data_type, end_date)
        
        # 4. 构建执行上下文
        context = await self._build_context(provider, deps, end_date)
        
        # 5. 执行更新
        try:
            await provider.renew_data_type(data_type, end_date, context)
        except Exception as e:
            # 6. 失败处理和降级
            await self._handle_failure(data_type, provider_name, e)
    
    async def renew_all_providers(self, end_date: str):
        """
        更新所有Provider（按依赖顺序）
        """
        order = self.resolve_execution_order()
        
        for provider_name in order:
            provider = self.registry.get(provider_name)
            context = await self._build_context(provider, [], end_date)
            
            try:
                await provider.renew_all(end_date, context)
            except Exception as e:
                logger.error(f"Provider {provider_name} 更新失败: {e}")
                # 根据配置决定是否继续
                if self.config.get('stop_on_error', False):
                    raise
    
    async def _is_data_available(self, data_type: str, end_date: str) -> bool:
        """检查数据是否可用"""
        # 查询数据库最新记录
        table_name = self.config['data_types'][data_type]['table']
        model = self.data_manager.get_model(table_name)
        latest = model.load_latest_records()
        
        if not latest:
            return False
        
        # 检查是否已更新到end_date
        # ...
        return True
    
    async def _build_context(self, provider, deps, end_date) -> ExecutionContext:
        """构建执行上下文"""
        context = ExecutionContext(end_date=end_date)
        
        # 添加依赖数据
        for dep in deps:
            if dep.pass_data:
                for data_type in dep.data_types:
                    data = await self._fetch_dependency_data(data_type, end_date)
                    context.add_dependency(data_type, data)
        
        return context
    
    async def _handle_failure(self, data_type: str, provider_name: str, error: Exception):
        """处理失败和降级"""
        # 检查是否有降级策略
        fallback_config = self.config['data_types'][data_type].get('fallback')
        
        if not fallback_config:
            raise error
        
        if fallback_config['strategy'] == 'cascade':
            # 尝试备用Provider
            providers = fallback_config['providers']
            for backup in providers:
                if backup != provider_name:
                    try:
                        backup_provider = self.registry.get(backup)
                        await backup_provider.renew_data_type(data_type, ...)
                        logger.info(f"降级成功：使用 {backup} 代替 {provider_name}")
                        return
                    except Exception as e:
                        logger.warning(f"备用Provider {backup} 也失败: {e}")
        
        # 所有降级都失败
        raise error
```

**优点：**
- 自动解析依赖
- 递归确保依赖满足
- 支持降级策略
- 集中的错误处理

---

### 改进方案 4：动态挂载（ProviderRegistry）

```python
class ProviderRegistry:
    """
    Provider 注册表
    
    职责：
    1. 动态挂载/卸载Provider
    2. 管理Provider生命周期
    3. 提供Provider查询
    """
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._metadata: Dict[str, ProviderMetadata] = {}
        self._data_type_index: Dict[str, List[str]] = {}  # data_type -> [provider_names]
    
    def mount(self, name: str, provider: BaseProvider):
        """
        挂载Provider
        
        Args:
            name: Provider名称
            provider: Provider实例或类
        """
        # 如果是类，实例化
        if isinstance(provider, type):
            provider = provider()
        
        # 验证接口
        if not isinstance(provider, BaseProvider):
            raise ValueError(f"{name} must implement BaseProvider")
        
        # 获取元数据
        info = provider.get_provider_info()
        metadata = ProviderMetadata(
            name=info.name,
            provides=info.provides,
            dependencies=info.dependencies
        )
        
        # 注册
        self._providers[name] = provider
        self._metadata[name] = metadata
        
        # 更新索引
        for data_type in info.provides:
            if data_type not in self._data_type_index:
                self._data_type_index[data_type] = []
            self._data_type_index[data_type].append(name)
        
        logger.info(f"✅ Provider '{name}' 已挂载，提供: {info.provides}")
    
    def unmount(self, name: str):
        """卸载Provider"""
        if name in self._providers:
            # 清理索引
            metadata = self._metadata[name]
            for data_type in metadata.provides:
                self._data_type_index[data_type].remove(name)
            
            # 删除
            del self._providers[name]
            del self._metadata[name]
            logger.info(f"Provider '{name}' 已卸载")
    
    def get(self, name: str) -> BaseProvider:
        """获取Provider"""
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """列出所有Provider"""
        return list(self._providers.keys())
    
    def get_providers_for(self, data_type: str) -> List[str]:
        """获取支持某数据类型的所有Provider"""
        return self._data_type_index.get(data_type, [])
    
    def get_metadata(self, name: str) -> ProviderMetadata:
        """获取Provider元数据"""
        return self._metadata.get(name)
```

**优点：**
- 支持运行时挂载/卸载
- 自动构建索引
- 验证接口一致性
- 便于测试（挂载Mock）

---

### 改进方案 5：配置化（统一配置）

```yaml
# config/data_source.yaml

# Provider配置
providers:
  tushare:
    enabled: true
    class: "app.data_source.providers.tushare.TushareAdapter"
    priority: 1
    auth:
      token_file: "app/data_source/providers/tushare/auth/token.txt"
    rate_limits:
      default: 200
      stock_kline: 500
    retry:
      max_attempts: 3
      backoff: exponential
  
  akshare:
    enabled: true
    class: "app.data_source.providers.akshare.AKShareAdapter"
    priority: 2
    rate_limits:
      default: 1000

# 数据类型配置
data_types:
  stock_kline:
    table: stock_kline
    primary_provider: tushare
    fallback_providers: [akshare]  # 降级
    renew_mode: incremental
    job_mode: multithread
    workers: 4
  
  adj_factor:
    table: adj_factor
    primary_provider: akshare
    dependencies:
      - data_type: stock_kline
        provider: tushare
        when: before_renew
        required: true
    renew_mode: incremental

# 全局配置
global:
  stop_on_error: false
  enable_cache: true
  cache_ttl: 3600
```

**优点：**
- 声明式配置
- 易于理解和修改
- 支持热加载
- 便于版本控制

---

## 📊 改进优先级

### P0（必须改进）
1. ✅ **统一接口（BaseProvider）**
   - 影响：可扩展性的基础
   - 工作量：2-3天
   
2. ✅ **依赖声明（ProviderMetadata）**
   - 影响：解决硬编码依赖
   - 工作量：1-2天
   
3. ✅ **数据协调器（DataCoordinator）**
   - 影响：自动处理依赖
   - 工作量：3-4天

### P1（重要改进）
4. ✅ **动态挂载（ProviderRegistry）**
   - 影响：可插拔性
   - 工作量：1-2天
   
5. ✅ **配置化（YAML配置）**
   - 影响：易用性
   - 工作量：1-2天

### P2（可选改进）
6. 🔵 **降级策略**
   - 影响：容错性
   - 工作量：2-3天
   
7. 🔵 **健康检查**
   - 影响：监控
   - 工作量：1天

---

## 🎯 总结

### 核心改进点

1. **统一接口** → 解决接口不一致
2. **依赖声明** → 解决硬编码依赖
3. **数据协调** → 解决依赖管理混乱
4. **动态挂载** → 支持可插拔
5. **配置化** → 提升易用性

### 新架构预览

```
DataSourceManager（统一管理器）
    ↓
ProviderRegistry（动态挂载）
    ├── TushareAdapter（适配器）→ Legacy Tushare
    ├── AKShareAdapter（适配器）→ Legacy AKShare
    └── WindAdapter（新Provider）
    ↓
DataCoordinator（协调器）
    ├── 依赖解析
    ├── 执行顺序
    ├── 降级策略
    └── 错误处理
```

### 扩展新Provider示例

```python
# 1. 实现接口
class WindProvider(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="wind",
            provides=["financial_news"],
            dependencies=[
                Dependency(
                    provider="tushare",
                    data_types=["stock_list"]
                )
            ]
        )
    
    async def renew_all(self, end_date, context):
        # 从context获取依赖数据
        stock_list = context.get_dependency('stock_list')
        # ... 实现更新逻辑

# 2. 挂载Provider
registry.mount('wind', WindProvider)

# 3. 自动工作
# - 依赖图自动更新
# - 执行顺序自动计算
# - 依赖数据自动传递
```

**完全无需修改现有代码！**

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

