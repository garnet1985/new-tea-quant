# 灵活性与粒度设计

## 核心问题

1. **灵活性**：用户能否手动干预自动化流程？
2. **粒度**：K线多周期是一个data_type还是多个？

---

## 🎯 问题1：手动干预机制

### 你的理解完全正确！

- ✅ 单Provider场景：直接调用，不需要Coordinator
- ✅ 多Provider场景：通过Coordinator自动协调

### 设计原则：**多层次灵活性**

```
Level 1: 自动化（推荐）
    ↓
Level 2: 半自动（可控）
    ↓
Level 3: 完全手动（Hack）
```

---

## 💡 Level 1: 自动化（推荐）

### 场景：99%的情况

```python
# 完全自动，依赖自动处理
await data_source.renew_all(end_date='20250101')

# 或者
await data_source.renew_data_type('adj_factor', end_date='20250101')
```

---

## 🔧 Level 2: 半自动化（可控）

### 场景：需要更细粒度控制

```python
# ========== 方式1：跳过依赖检查 ==========
await coordinator.coordinate_update(
    'adj_factor', 
    end_date='20250101',
    skip_dependency_check=True  # ⭐ 跳过依赖检查
)

# 用例：我知道K线数据已经是最新的，不要再检查了


# ========== 方式2：只检查不更新 ==========
is_available = await coordinator.check_data_available(
    'stock_kline',
    end_date='20250101'
)

if not is_available:
    # 自己决定怎么处理
    print("K线数据不可用，手动处理...")
    await custom_update_kline()


# ========== 方式3：自定义执行顺序 ==========
# 不使用自动计算的顺序
custom_order = ['akshare', 'tushare']  # 反向顺序

for provider_name in custom_order:
    provider = coordinator.registry.get(provider_name)
    context = await coordinator._build_context(provider_name, end_date)
    await provider.renew_all(end_date, context)


# ========== 方式4：注入自定义Context ==========
custom_context = ExecutionContext(
    end_date='20250101',
    stock_list=['000001.SZ', '600000.SH'],  # ⭐ 只更新这两只
    dependencies={'custom_data': my_custom_data}  # ⭐ 注入自定义数据
)

provider = coordinator.registry.get('akshare')
await provider.renew_all(end_date, custom_context)


# ========== 方式5：部分依赖满足 ==========
# 手动满足部分依赖，让Coordinator处理剩余部分
await coordinator.coordinate_update(
    'adj_factor',
    end_date='20250101',
    provided_dependencies={  # ⭐ 我已经准备好了部分依赖
        'stock_kline': my_kline_data
    }
)
```

---

## 🛠️ Level 3: 完全手动（Hack）

### 场景：特殊场景，需要完全控制

```python
# ========== 方式1：直接调用Provider（绕过Coordinator）==========
tushare = coordinator.registry.get('tushare')

# 直接调用，完全控制
await tushare._legacy.stock_kline_renewer.renew(
    latest_market_open_day='20250101',
    stock_list=['000001.SZ']  # 只更新一只
)


# ========== 方式2：临时修改依赖关系 ==========
# 临时移除某个依赖
akshare = coordinator.registry.get('akshare')
original_info = akshare.get_provider_info()

# Hack：创建临时Provider（无依赖版本）
class AKShareNoDeps(AKShareAdapter):
    def get_provider_info(self):
        info = super().get_provider_info()
        info.dependencies = []  # ⭐ 移除所有依赖
        return info

# 临时替换
coordinator.registry.unmount('akshare')
coordinator.registry.mount('akshare', AKShareNoDeps(data_manager))

# 执行
await coordinator.coordinate_update('adj_factor', '20250101')

# 恢复
coordinator.registry.unmount('akshare')
coordinator.registry.mount('akshare', AKShareAdapter(data_manager))


# ========== 方式3：中间拦截（Hook机制）⭐ 推荐 ==========
class CustomCoordinator(DataCoordinator):
    """扩展Coordinator，添加Hook"""
    
    async def before_provider_renew(self, provider_name: str, context: ExecutionContext):
        """在Provider更新前调用（Hook）"""
        print(f"🔔 准备更新 {provider_name}")
        
        # 自定义逻辑
        if provider_name == 'akshare':
            # 修改context
            context.stock_list = context.stock_list[:10]  # 只更新前10只
            print(f"⚠️  已限制为前10只股票")
    
    async def after_provider_renew(self, provider_name: str, success: bool):
        """在Provider更新后调用（Hook）"""
        if not success:
            print(f"❌ {provider_name} 更新失败，执行自定义恢复逻辑...")
            await self.custom_recovery(provider_name)
    
    async def renew_all_providers(self, end_date: str):
        """重写，添加Hook调用"""
        order = self.resolve_execution_order()
        
        for provider_name in order:
            provider = self.registry.get(provider_name)
            context = await self._build_context(provider_name, end_date)
            
            # ⭐ Hook: before
            await self.before_provider_renew(provider_name, context)
            
            try:
                await provider.renew_all(end_date, context)
                
                # ⭐ Hook: after (success)
                await self.after_provider_renew(provider_name, True)
            except Exception as e:
                # ⭐ Hook: after (failure)
                await self.after_provider_renew(provider_name, False)
                raise

# 使用自定义Coordinator
custom_coordinator = CustomCoordinator(registry, data_manager)
await custom_coordinator.renew_all_providers('20250101')


# ========== 方式4：事件监听（观察者模式）⭐ 最灵活 ==========
class DataSourceEventListener:
    """事件监听器"""
    
    def on_before_check_dependency(self, data_type: str, dependency: Dependency):
        """依赖检查前"""
        print(f"检查依赖: {data_type} → {dependency.provider}")
    
    def on_dependency_missing(self, data_type: str, dependency: Dependency):
        """依赖缺失时"""
        print(f"⚠️  依赖缺失: {dependency.provider}.{dependency.data_types}")
        
        # 可以在这里hack
        if data_type == 'adj_factor':
            print("使用备用数据源...")
            return 'use_fallback'
    
    def on_provider_start(self, provider_name: str):
        """Provider开始更新"""
        print(f"▶️  {provider_name} 开始更新")
    
    def on_provider_complete(self, provider_name: str, duration: float):
        """Provider更新完成"""
        print(f"✅ {provider_name} 完成，耗时 {duration:.2f}s")

# 注册监听器
coordinator.add_listener(DataSourceEventListener())

# 执行（自动触发事件）
await coordinator.renew_all_providers('20250101')
```

---

## 🎯 推荐的Hack接口设计

### DataCoordinator 扩展接口

```python
class DataCoordinator:
    def __init__(self, registry, data_manager):
        self.registry = registry
        self.data_manager = data_manager
        self._listeners = []  # ⭐ 事件监听器
        self._hooks = {}      # ⭐ Hook函数
    
    # ========== 事件监听 ==========
    
    def add_listener(self, listener):
        """注册事件监听器"""
        self._listeners.append(listener)
    
    def _emit_event(self, event_name: str, **kwargs):
        """触发事件"""
        for listener in self._listeners:
            handler = getattr(listener, f'on_{event_name}', None)
            if handler:
                result = handler(**kwargs)
                if result:  # 监听器可以返回结果来影响流程
                    return result
    
    # ========== Hook机制 ==========
    
    def register_hook(self, hook_name: str, func):
        """注册Hook函数"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(func)
    
    def _call_hooks(self, hook_name: str, **kwargs):
        """调用Hook"""
        if hook_name in self._hooks:
            for func in self._hooks[hook_name]:
                func(**kwargs)
    
    # ========== 扩展的coordinate方法 ==========
    
    async def coordinate_update(
        self,
        data_type: str,
        end_date: str,
        skip_dependency_check: bool = False,  # ⭐ 跳过依赖检查
        provided_dependencies: Dict = None,    # ⭐ 预提供的依赖
        force_update: bool = False,            # ⭐ 强制更新（即使数据已是最新）
        custom_context: ExecutionContext = None  # ⭐ 自定义context
    ):
        """扩展的协调方法"""
        
        # 触发事件
        self._emit_event('before_coordinate', data_type=data_type)
        
        providers = self.registry.get_providers_for(data_type)
        provider_name = providers[0]
        provider = self.registry.get(provider_name)
        metadata = self.registry.get_metadata(provider_name)
        
        # 依赖检查（可跳过）
        if not skip_dependency_check:
            for dep in metadata.dependencies:
                if dep.when == "before_renew":
                    for dep_data_type in dep.data_types:
                        # 检查是否已预提供
                        if provided_dependencies and dep_data_type in provided_dependencies:
                            continue
                        
                        # 检查是否可用
                        is_available = await self._is_data_available(dep_data_type, end_date)
                        
                        if not is_available or force_update:
                            # 触发事件（允许拦截）
                            action = self._emit_event(
                                'dependency_missing',
                                data_type=data_type,
                                dependency=dep
                            )
                            
                            if action == 'skip':
                                continue
                            elif action == 'use_fallback':
                                await self._use_fallback_data(dep_data_type)
                                continue
                            
                            # 默认：递归更新
                            await self.coordinate_update(dep_data_type, end_date)
        
        # 构建context
        if custom_context:
            context = custom_context
        else:
            context = await self._build_context(provider_name, end_date)
            
            # 注入预提供的依赖
            if provided_dependencies:
                if not context.dependencies:
                    context.dependencies = {}
                context.dependencies.update(provided_dependencies)
        
        # 调用Hook
        self._call_hooks('before_provider_renew', 
                        provider_name=provider_name, 
                        context=context)
        
        # 执行更新
        await provider.renew_data_type(data_type, end_date, context)
        
        # 调用Hook
        self._call_hooks('after_provider_renew',
                        provider_name=provider_name)
        
        # 触发事件
        self._emit_event('after_coordinate', data_type=data_type)
```

---

## 📊 问题2：K线多周期的粒度设计

### 设计方案对比

#### 方案A：一个data_type，包含多个周期（❌ 不推荐）

```python
# ❌ 问题：粒度太粗
class TushareAdapter:
    def get_provider_info(self):
        return ProviderInfo(
            provides=["stock_kline"]  # 包含日/周/月线
        )
    
    async def renew_data_type(self, data_type, end_date, context):
        if data_type == "stock_kline":
            # 必须全部更新，无法单独更新日线
            await self._update_daily()
            await self._update_weekly()
            await self._update_monthly()

# ❌ 问题：
# 1. 无法只更新日线
# 2. 无法灵活组合
# 3. 依赖关系不清晰
```

#### 方案B：多个data_type，分别独立（✅ 推荐）

```python
# ✅ 推荐：每个周期独立
class TushareAdapter:
    def get_provider_info(self):
        return ProviderInfo(
            provides=[
                "stock_kline_daily",    # 日线
                "stock_kline_weekly",   # 周线
                "stock_kline_monthly",  # 月线
            ]
        )
    
    async def renew_data_type(self, data_type, end_date, context):
        if data_type == "stock_kline_daily":
            await self._update_daily()
        elif data_type == "stock_kline_weekly":
            await self._update_weekly()
        elif data_type == "stock_kline_monthly":
            await self._update_monthly()

# ✅ 优点：
# 1. 可以只更新日线
# 2. 可以灵活组合
# 3. 依赖关系清晰

# 使用：
await data_source.renew_data_type('stock_kline_daily', '20250101')  # 只更新日线
await data_source.renew_data_type('stock_kline_weekly', '20250101')  # 只更新周线
```

#### 方案C：层次化data_type（✅ 最灵活）

```python
# ✅ 最灵活：支持组合和独立
class TushareAdapter:
    def get_provider_info(self):
        return ProviderInfo(
            provides=[
                # 独立的data_type
                "stock_kline_daily",
                "stock_kline_weekly",
                "stock_kline_monthly",
                
                # 组合的data_type（语法糖）
                "stock_kline_all"  # 包含上面三个
            ]
        )
    
    async def renew_data_type(self, data_type, end_date, context):
        if data_type == "stock_kline_daily":
            await self._update_daily()
        
        elif data_type == "stock_kline_weekly":
            await self._update_weekly()
        
        elif data_type == "stock_kline_monthly":
            await self._update_monthly()
        
        elif data_type == "stock_kline_all":
            # 组合：调用三个独立的
            await self.renew_data_type("stock_kline_daily", end_date, context)
            await self.renew_data_type("stock_kline_weekly", end_date, context)
            await self.renew_data_type("stock_kline_monthly", end_date, context)

# ✅ 使用：
# 场景1：只更新日线
await data_source.renew_data_type('stock_kline_daily', '20250101')

# 场景2：更新所有周期
await data_source.renew_data_type('stock_kline_all', '20250101')

# 场景3：自定义组合
await data_source.renew_data_type('stock_kline_daily', '20250101')
await data_source.renew_data_type('stock_kline_monthly', '20250101')
# 跳过周线
```

---

## 🎯 推荐的K线粒度设计

### 完整实现

```python
# app/data_source/v2/adapters/tushare_adapter.py

class TushareAdapter(BaseProvider):
    
    def get_provider_info(self):
        return ProviderInfo(
            name="tushare",
            provides=[
                # === 基础数据 ===
                "stock_list",
                
                # === K线数据（独立周期）===
                "stock_kline_daily",      # 日线
                "stock_kline_weekly",     # 周线  
                "stock_kline_monthly",    # 月线
                
                # === K线组合（语法糖）===
                "stock_kline_all",        # 所有周期
                
                # === 其他数据 ===
                "corporate_finance",
                "gdp",
                # ...
            ],
            dependencies=[]
        )
    
    def supports_data_type(self, data_type: str) -> bool:
        """检查是否支持某个data_type"""
        info = self.get_provider_info()
        return data_type in info.provides
    
    async def renew_data_type(self, data_type: str, end_date: str, context: ExecutionContext):
        """更新指定数据类型"""
        stock_list = context.stock_list if context else None
        
        # === 独立周期 ===
        if data_type == "stock_kline_daily":
            return await self._renew_kline(end_date, stock_list, freq='daily')
        
        elif data_type == "stock_kline_weekly":
            return await self._renew_kline(end_date, stock_list, freq='weekly')
        
        elif data_type == "stock_kline_monthly":
            return await self._renew_kline(end_date, stock_list, freq='monthly')
        
        # === 组合 ===
        elif data_type == "stock_kline_all":
            logger.info("📊 更新所有K线周期...")
            await self._renew_kline(end_date, stock_list, freq='daily')
            await self._renew_kline(end_date, stock_list, freq='weekly')
            await self._renew_kline(end_date, stock_list, freq='monthly')
            logger.info("✅ 所有K线周期更新完成")
            return True
        
        # === 其他数据类型 ===
        elif data_type == "corporate_finance":
            return self._legacy.corporate_finance_renewer.renew(end_date, stock_list)
        
        # ...
    
    async def _renew_kline(self, end_date: str, stock_list: list, freq: str):
        """
        更新K线（内部方法）
        
        Args:
            freq: 'daily' | 'weekly' | 'monthly'
        """
        # 根据频率选择对应的renewer
        renewer_map = {
            'daily': self._legacy.stock_kline_renewer,
            'weekly': self._legacy.stock_kline_weekly_renewer,   # 假设有
            'monthly': self._legacy.stock_kline_monthly_renewer  # 假设有
        }
        
        renewer = renewer_map.get(freq)
        if not renewer:
            raise ValueError(f"不支持的频率: {freq}")
        
        return renewer.renew(end_date, stock_list)
```

### 使用示例

```python
# ========== 场景1：只更新日线 ==========
await data_source.renew_data_type('stock_kline_daily', '20250101')
# ✅ 快速，只更新日线

# ========== 场景2：更新所有周期 ==========
await data_source.renew_data_type('stock_kline_all', '20250101')
# ✅ 完整，三个周期都更新

# ========== 场景3：自定义组合 ==========
await data_source.renew_data_type('stock_kline_daily', '20250101')
await data_source.renew_data_type('stock_kline_monthly', '20250101')
# ✅ 灵活，只更新日线和月线，跳过周线

# ========== 场景4：通过Coordinator批量更新 ==========
await coordinator.coordinate_update('stock_kline_all', '20250101')
# ✅ 自动处理依赖（如果有）

# ========== 场景5：手动控制（Hack）==========
tushare = coordinator.registry.get('tushare')
await tushare._renew_kline('20250101', ['000001.SZ'], freq='daily')
# ✅ 完全控制，只更新一只股票的日线
```

---

## 🎯 依赖关系示例

### 场景：复权因子依赖日线（不依赖周线和月线）

```python
class AKShareAdapter(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="akshare",
            provides=["adj_factor"],
            dependencies=[
                Dependency(
                    provider="tushare",
                    data_types=["stock_kline_daily"],  # ⭐ 只依赖日线
                    when="before_renew",
                    required=True
                )
            ]
        )

# 使用：
await coordinator.coordinate_update('adj_factor', '20250101')

# ✅ Coordinator自动：
# 1. 检查 stock_kline_daily 是否可用
# 2. 如果不可用，先更新日线
# 3. 然后更新复权因子
# 4. 不会更新周线和月线（不需要）
```

---

## 📋 配置文件示例（可选）

```yaml
# config/data_source.yaml

data_types:
  # === K线数据（独立） ===
  stock_kline_daily:
    provider: tushare
    table: stock_kline
    description: "股票日K线数据"
    frequency: daily
  
  stock_kline_weekly:
    provider: tushare
    table: stock_kline_weekly
    description: "股票周K线数据"
    frequency: weekly
  
  stock_kline_monthly:
    provider: tushare
    table: stock_kline_monthly
    description: "股票月K线数据"
    frequency: monthly
  
  # === K线组合（语法糖） ===
  stock_kline_all:
    provider: tushare
    description: "所有K线周期（日/周/月）"
    composite: true  # 标记为组合类型
    includes:
      - stock_kline_daily
      - stock_kline_weekly
      - stock_kline_monthly
  
  # === 复权因子 ===
  adj_factor:
    provider: akshare
    table: adj_factor
    dependencies:
      - data_type: stock_kline_daily  # ⭐ 只依赖日线
        provider: tushare
```

---

## 🎯 总结

### 问题1：手动干预机制

| Level | 方式 | 场景 | 复杂度 |
|-------|------|------|--------|
| **Level 1** | 自动化 | 99%情况 | 🟢 简单 |
| **Level 2** | 半自动 | 需要部分控制 | 🟡 中等 |
| **Level 3** | 完全手动 | 特殊Hack场景 | 🔴 复杂 |

**推荐实现**：
1. ✅ 提供`skip_dependency_check`等参数（Level 2）
2. ✅ 提供Hook机制和事件监听（Level 2-3）
3. ✅ 允许直接访问Provider（Level 3）

### 问题2：K线多周期粒度

| 方案 | 优点 | 缺点 | 推荐 |
|-----|------|------|------|
| **一个data_type** | 简单 | 不灵活 | ❌ |
| **多个data_type** | 灵活 | 代码稍多 | ✅ |
| **层次化** | 最灵活 | 稍复杂 | ⭐ |

**推荐设计**：
- ✅ `stock_kline_daily`, `stock_kline_weekly`, `stock_kline_monthly`（独立）
- ✅ `stock_kline_all`（组合，语法糖）
- ✅ 依赖只依赖需要的周期（如`adj_factor`只依赖`stock_kline_daily`）

### 核心思想

```
灵活性 = 自动化 + 可控性 + Hack接口

粒度 = 独立data_type + 组合语法糖
```

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

