# 示例：获取复权因子数据

## 场景描述

复权因子（adj_factor）是一个典型的"跨Provider依赖"场景：
- **提供者**：AKShare
- **依赖**：需要Tushare先提供K线数据
- **原因**：AKShare的复权因子计算需要基于K线数据的日期范围

---

## 🎯 新架构下的完整流程

### 1. AKShare Provider 声明依赖

```python
# app/data_source/v2/adapters/akshare_adapter.py

class AKShareAdapter(BaseProvider):
    
    def get_provider_info(self) -> ProviderInfo:
        """声明元数据和依赖"""
        return ProviderInfo(
            name="akshare",
            version="1.0.0",
            provides=["adj_factor"],  # 我提供复权因子
            dependencies=[
                Dependency(
                    provider="tushare",              # 依赖Tushare
                    data_types=["stock_kline"],      # 需要K线数据
                    when="before_renew",             # 更新前必须满足
                    required=True,                   # 必需依赖
                    pass_data=False                  # 不需要传递数据，只需确保DB中有
                )
            ],
            requires_auth=False
        )
    
    async def renew_all(self, end_date: str, context: ExecutionContext = None):
        """
        更新复权因子
        
        此时可以确保：
        - Tushare已经更新完成
        - stock_kline表中已有数据
        - context中包含stock_list
        """
        # 获取股票列表（由Coordinator提供）
        stock_list = context.stock_list if context else []
        
        logger.info(f"📊 开始更新复权因子，共 {len(stock_list)} 只股票")
        
        # 调用Legacy实现（保留所有功能）
        return await self._legacy.renew(end_date, stock_list)
```

---

### 2. 用户代码：简单调用

#### 方式1：更新所有Provider（推荐）

```python
# start.py 或业务代码

async def renew_all_data():
    """更新所有数据（按依赖顺序自动执行）"""
    
    # 获取DataSourceManager
    data_source = DataSourceManager(data_manager)
    
    # 一行代码，自动处理所有依赖
    await data_source.renew_all(end_date='20250101')
    
    # ✅ 自动执行：
    # 1. Tushare: 更新stock_list
    # 2. Tushare: 更新stock_kline （AKShare的依赖）
    # 3. Tushare: 更新其他数据（gdp, shibor等）
    # 4. AKShare: 更新adj_factor （此时K线已存在）
```

#### 方式2：只更新复权因子（智能）

```python
async def renew_adj_factor_only():
    """只更新复权因子（自动处理依赖）"""
    
    data_source = DataSourceManager(data_manager)
    
    # 只请求复权因子
    await data_source.renew_data_type('adj_factor', end_date='20250101')
    
    # ✅ Coordinator自动处理：
    # 1. 检查：stock_kline是否已更新到20250101？
    # 2. 如果没有 → 先调用Tushare更新K线
    # 3. 如果有 → 直接更新复权因子
```

---

### 3. DataCoordinator 自动协调（内部实现）

```python
# app/data_source/v2/data_coordinator.py

class DataCoordinator:
    
    async def renew_all_providers(self, end_date: str):
        """
        方式1：更新所有Provider
        
        自动计算执行顺序
        """
        # Step 1: 构建依赖图
        self._dependency_graph = self.build_dependency_graph()
        
        # Step 2: 拓扑排序（自动计算顺序）
        order = self._dependency_graph.topological_sort()
        # 结果: ['tushare', 'akshare']
        
        logger.info(f"📋 Provider执行顺序: {' → '.join(order)}")
        
        # Step 3: 按顺序执行
        for provider_name in order:
            provider = self.registry.get(provider_name)
            
            # 构建执行上下文
            context = await self._build_context(provider_name, end_date)
            
            # 执行更新
            logger.info(f"▶️  更新 {provider_name}...")
            await provider.renew_all(end_date, context)
            logger.info(f"✅ {provider_name} 更新完成")
    
    async def coordinate_update(self, data_type: str, end_date: str):
        """
        方式2：更新指定数据类型
        
        递归确保依赖满足
        """
        logger.info(f"🎯 请求更新数据类型: {data_type}")
        
        # Step 1: 找到负责的Provider
        providers = self.registry.get_providers_for(data_type)
        provider_name = providers[0]  # akshare
        provider = self.registry.get(provider_name)
        
        # Step 2: 获取依赖列表
        metadata = self.registry.get_metadata(provider_name)
        # dependencies = [Dependency(provider='tushare', data_types=['stock_kline'], ...)]
        
        # Step 3: 确保依赖满足
        for dep in metadata.dependencies:
            if dep.when == "before_renew":
                for dep_data_type in dep.data_types:
                    # 检查K线数据是否可用
                    is_available = await self._is_data_available(
                        dep_data_type,  # 'stock_kline'
                        end_date
                    )
                    
                    if not is_available:
                        logger.info(f"🔗 依赖数据 {dep_data_type} 不可用，先更新...")
                        
                        # ⭐ 递归调用（自动处理依赖链）
                        await self.coordinate_update(dep_data_type, end_date)
        
        # Step 4: 构建执行上下文
        context = await self._build_context(provider_name, end_date)
        
        # Step 5: 执行更新
        logger.info(f"▶️  更新 {provider_name}.{data_type}")
        await provider.renew_data_type(data_type, end_date, context)
        logger.info(f"✅ {data_type} 更新完成")
    
    async def _is_data_available(self, data_type: str, end_date: str) -> bool:
        """
        检查数据是否可用
        
        逻辑：
        1. 查询数据库最新记录
        2. 检查是否已更新到end_date
        """
        # 映射：data_type → table_name
        table_mapping = {
            'stock_kline': 'stock_kline',
            'adj_factor': 'adj_factor',
        }
        
        table_name = table_mapping.get(data_type)
        if not table_name:
            return False
        
        # 查询数据库
        model = self.data_manager.get_model(table_name)
        latest_records = model.load_latest_records()
        
        if not latest_records:
            logger.info(f"❌ {data_type} 数据不存在")
            return False
        
        # 检查最新日期
        latest_date = max(r['trade_date'] for r in latest_records)
        
        if latest_date >= end_date:
            logger.info(f"✅ {data_type} 数据已是最新（{latest_date} >= {end_date}）")
            return True
        else:
            logger.info(f"⏰ {data_type} 数据需要更新（{latest_date} < {end_date}）")
            return False
    
    async def _build_context(self, provider_name: str, end_date: str) -> ExecutionContext:
        """
        构建执行上下文
        
        传递依赖数据（如果需要）
        """
        metadata = self.registry.get_metadata(provider_name)
        context = ExecutionContext(end_date=end_date)
        
        # 准备股票列表（如果需要）
        needs_stock_list = any(
            'stock_list' in dep.data_types or 'stock_kline' in dep.data_types
            for dep in metadata.dependencies
        )
        
        if needs_stock_list:
            # 从Tushare获取股票列表
            tushare = self.registry.get('tushare')
            stock_list = tushare.load_filtered_stock_list()
            context.stock_list = stock_list
            logger.info(f"📋 股票列表: {len(stock_list)} 只")
        
        # 传递依赖数据（如果需要）
        dependencies_data = {}
        for dep in metadata.dependencies:
            if dep.pass_data:
                # 从数据库加载依赖数据
                for data_type in dep.data_types:
                    data = await self._fetch_dependency_data(data_type, end_date)
                    dependencies_data[data_type] = data
        
        context.dependencies = dependencies_data
        
        return context
    
    async def _fetch_dependency_data(self, data_type: str, end_date: str):
        """
        从数据库获取依赖数据
        
        用于 pass_data=True 的情况
        """
        # 使用DataService查询
        if data_type == 'stock_kline':
            stock_service = self.data_manager.get_data_service('stock_related.stock')
            return stock_service.load_kline(end_date=end_date)
        
        # 其他数据类型...
        return None
```

---

## 📊 执行流程对比

### 场景1：更新所有数据

#### 旧架构（硬编码）
```python
async def renew_data(self, latest_market_open_day: str):
    tu = self.sources['tushare']
    
    # 1. 手动更新Tushare
    tu.stock_list_renewer.renew(latest_market_open_day)
    latest_stock_list = tu.load_filtered_stock_list()
    await tu.renew(latest_market_open_day, latest_stock_list)
    
    # 2. 手动注入依赖
    ak = self.sources['akshare']
    ak.inject_dependency(tu)  # ⚠️ 硬编码
    
    # 3. 手动更新AKShare
    await ak.renew(latest_market_open_day, latest_stock_list)
```

#### 新架构（自动）
```python
async def renew_all(self, end_date: str):
    # 一行搞定，自动处理所有依赖
    await self.coordinator.renew_all_providers(end_date)
    
    # ✅ 自动解析依赖图
    # ✅ 自动计算执行顺序
    # ✅ 自动传递stock_list
```

---

### 场景2：只更新复权因子

#### 旧架构（无法实现）
```python
# ❌ 无法单独更新adj_factor
# 因为：
# 1. 不知道是否需要先更新K线
# 2. 不知道如何注入依赖
# 3. 只能更新所有数据
```

#### 新架构（智能）
```python
async def renew_adj_factor():
    await data_source.renew_data_type('adj_factor', '20250101')
    
    # ✅ 自动检查K线是否存在
    # ✅ 如果不存在，自动更新K线
    # ✅ 然后更新复权因子
```

---

## 🔄 完整执行日志示例

### 场景：首次运行（DB为空）

```bash
$ python start.py renew

🔄 开始更新所有Provider，截止日期: 20250101
📋 Provider执行顺序: tushare → akshare

▶️  更新 tushare...
  📋 更新股票列表...
  ✅ 股票列表更新完成，共 5234 只股票
  
  📈 更新股票K线数据...
  ✅ 股票K线更新完成（5234只，多线程）
  
  🌍 更新宏观经济数据...
  ✅ GDP更新完成
  ✅ CPI/PPI/PMI更新完成
  ✅ Shibor更新完成
  ✅ LPR更新完成
  
✅ tushare 更新完成

▶️  更新 akshare...
  📋 股票列表: 5234 只
  
  🔗 检查依赖: stock_kline
  ✅ stock_kline 数据已是最新（20250101）
  
  📊 开始更新复权因子，共 5234 只股票
  ✅ 复权因子更新完成（5234只，多线程）
  
✅ akshare 更新完成

🎉 所有Provider更新完成
```

---

### 场景：增量更新（只更新复权因子）

```bash
$ python start.py renew --data-type adj_factor

🎯 请求更新数据类型: adj_factor

📋 找到Provider: akshare

🔗 检查依赖: stock_kline
  ⏰ stock_kline 数据需要更新（20241225 < 20250101）
  
  🔗 先更新依赖数据: stock_kline
  ▶️  更新 tushare.stock_kline
  📈 更新股票K线数据...
  ✅ 股票K线更新完成（5234只）
  
✅ 依赖满足，开始更新 adj_factor

▶️  更新 akshare.adj_factor
  📋 股票列表: 5234 只
  📊 开始更新复权因子，共 5234 只股票
  ✅ 复权因子更新完成（5234只）
  
✅ adj_factor 更新完成
```

---

## 🎯 扩展示例：多层依赖

### 场景：Choice依赖Wind，Wind依赖Tushare

```python
# Wind Provider
class WindProvider(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="wind",
            provides=["financial_news"],
            dependencies=[
                Dependency(
                    provider="tushare",
                    data_types=["stock_list"],
                    pass_data=True  # 需要传递股票列表
                )
            ]
        )

# Choice Provider
class ChoiceProvider(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="choice",
            provides=["analyst_rating"],
            dependencies=[
                Dependency(
                    provider="wind",
                    data_types=["financial_news"],
                    pass_data=True  # 需要新闻数据
                ),
                Dependency(
                    provider="akshare",
                    data_types=["adj_factor"],
                    pass_data=False  # 只需确保存在
                )
            ]
        )
```

### 自动执行顺序

```python
# 注册
registry.mount('tushare', TushareAdapter(dm))
registry.mount('akshare', AKShareAdapter(dm))
registry.mount('wind', WindProvider(dm))
registry.mount('choice', ChoiceProvider(dm))

# 自动计算执行顺序
coordinator = DataCoordinator(registry, dm)
order = coordinator.resolve_execution_order()

print(order)
# 输出: ['tushare', 'akshare', 'wind', 'choice']

# 执行
await coordinator.renew_all_providers('20250101')

# ✅ 自动执行：
# 1. tushare: 更新stock_list, stock_kline（akshare依赖）
# 2. akshare: 更新adj_factor（choice依赖）
# 3. wind: 更新financial_news（choice依赖，需要stock_list）
# 4. choice: 更新analyst_rating（需要news和adj_factor）
```

---

## 🔥 降级策略示例（可选功能）

### 场景：Tushare挂了，使用AKShare备用

```python
# 配置降级策略
data_source_config = {
    'data_types': {
        'stock_kline': {
            'providers': [
                {'name': 'tushare', 'priority': 1},
                {'name': 'akshare', 'priority': 2},  # 备用
            ],
            'fallback_strategy': 'cascade'
        }
    }
}

# DataCoordinator处理失败
async def _handle_failure(self, data_type, provider_name, error):
    """降级处理"""
    config = self.config['data_types'][data_type]
    fallback_config = config.get('fallback')
    
    if fallback_config['strategy'] == 'cascade':
        # 尝试备用Provider
        for provider_info in fallback_config['providers']:
            if provider_info['name'] != provider_name:
                backup_provider = self.registry.get(provider_info['name'])
                
                try:
                    logger.warning(f"⚠️  尝试备用Provider: {provider_info['name']}")
                    await backup_provider.renew_data_type(data_type, ...)
                    logger.info(f"✅ 降级成功：使用 {provider_info['name']}")
                    return
                except Exception as e:
                    logger.error(f"❌ 备用Provider也失败: {e}")
    
    # 所有降级都失败
    raise error
```

---

## 📋 总结

### 关键改进

| 场景 | 旧架构 | 新架构 |
|-----|--------|--------|
| **更新所有数据** | 手动编排顺序 | 自动计算顺序 |
| **依赖注入** | 手动inject_dependency | 自动传递context |
| **单独更新某数据** | 不支持 | 自动处理依赖 |
| **多层依赖** | 代码爆炸 | 递归自动处理 |
| **新增Provider** | 修改renew_data() | 只需mount() |
| **降级策略** | 无 | 支持cascade |

### 用户体验

**旧架构**：
```python
# 需要知道依赖关系
# 需要手动编排顺序
# 需要手动注入依赖
# 代码量大，容易出错
```

**新架构**：
```python
# 一行代码
await data_source.renew_all(end_date)

# 或者
await data_source.renew_data_type('adj_factor', end_date)

# 所有依赖自动处理！
```

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

