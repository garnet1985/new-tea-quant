# DataService 层设计文档

## 设计背景

本项目的核心特点是**配置驱动的数据读取**：策略作者通过 `settings.py` 声明所需数据，框架自动获取并注入。

DataService 层负责：
1. 提供领域级的数据访问方法
2. 处理跨表查询和数据组装
3. 支持配置驱动的数据分发

## 数据分类

根据数据特性和使用场景，将所有数据分为 **3 大类**：

### 1. `stock_related/` - 股票相关数据

与具体股票 `ts_code` 直接关联的数据。

**包含：**
- 股票基础信息、K线数据、标签
- 财务指标（利润表、现金流、资产负债表）
- 行业信息、板块信息

**特点：**
- 每只股票都有独立的数据
- 查询时通常需要 `ts_code` 参数
- 同一股票的不同维度数据经常一起使用（如 K线 + 财务）

### 2. `macro_system/` - 宏观/系统数据

与个股无关的全局性数据。

**包含：**
- 宏观经济指标（GDP、CPI、PPI、PMI、货币供应量）
- 利率数据（Shibor、LPR）
- 交易日历、元信息

**特点：**
- 所有股票共享同一份数据
- 只与时间相关，不与具体股票相关
- 模拟时全局缓存一份即可

### 3. `ui_transit/` - UI/中转数据

为前端展示或系统流转存储的数据。

**包含：**
- 投资操作记录（买入、卖出、持仓）
- 扫描结果
- 策略运行日志

**特点：**
- 用于数据展示和追溯
- 与业务流程相关
- 可能涉及多表联查（如投资记录 + 股票信息）

---

## 目录结构

```
app/core_modules/data_manager/data_services/
├── DESIGN.md                           # 本文档
├── __init__.py                         # 导出 BaseDataService
│
├── stock_related/                      # 大类1：股票相关
│   ├── __init__.py                     # 导出 StockRelatedDataService（大类统一接口）
│   ├── stock/
│   │   └── stock_data_service.py       # 股票基础数据（K线、标签、列表）
│   ├── corporate_finance/
│   │   └── corporate_finance_data_service.py  # 财务数据
│   └── industry/
│       └── industry_data_service.py    # 行业/板块数据（待实现）
│
├── macro_system/                       # 大类2：宏观/系统
│   ├── __init__.py                     # 导出 MacroSystemDataService
│   └── macro/
│       └── macro_data_service.py       # 宏观经济数据（GDP、CPI、Shibor等）
│
└── ui_transit/                         # 大类3：UI/中转
    ├── __init__.py                     # 导出 UiTransitDataService
    └── investment/
        └── investment_data_service.py  # 投资记录数据（待实现）
```

---

## 核心设计原则

### 1. 配置驱动优先

策略作者通过配置声明需求，框架自动分发数据：

```python
# strategy/settings.py
data_requirements = {
    'stock_kline': {'columns': ['open', 'close', 'high', 'low']},
    'corporate_finance': {'indicators': ['revenue', 'profit']},
    'macro_economy': {'indicators': ['shibor', 'lpr']}
}

# strategy/strategy.py
def scan_opportunity(context: dict):
    kline = context['stock_kline']        # 框架自动注入
    finance = context['corporate_finance']
    macro = context['macro_economy']
    # 策略只负责逻辑，不负责数据获取
```

### 2. 简洁性 > 性能优化

**关键认知：**
- Simulator 对每只股票的数据只查询**一次**，后续都是缓存读取
- 宏观数据全局共享，只查询**一次**
- JOIN 的性能收益微乎其微（只在第一次查询时有效）

**因此：**
- 优先保证代码简洁、易读、易维护
- 默认使用"多次查询"（分别查表），依赖缓存保证性能
- 只在确认高频场景有瓶颈时，才添加 JOIN 优化

### 3. 大类内可组合，跨大类分别查

**大类内组合（可选，按需优化）：**
```python
# stock_related/__init__.py
class StockRelatedDataService:
    def load_stock_with_finance(self, ts_code: str, date: str):
        """预设的优化查询：K线 + 财务数据"""
        # 如果发现这个组合高频使用，可以用 JOIN 优化
        pass
```

**跨大类查询（由调用方处理）：**
```python
# DataManager.resolve_data_requirements()
def resolve_data_requirements(settings, context):
    result = {}
    
    # 分别查询，不做跨大类 JOIN
    if 'stock_kline' in settings:
        result['stock_kline'] = self.get_data_service('stock_related.stock').load_kline(...)
    
    if 'macro_economy' in settings:
        result['macro_economy'] = self.get_data_service('macro_system.macro').load_macro_snapshot(...)
    
    return result
```

### 4. 两级访问机制

支持通过大类或子 Service 访问：

```python
# 访问大类（用于大类内组合查询）
stock_related_service = data_manager.get_data_service('stock_related')
combined = stock_related_service.load_stock_with_finance(...)

# 访问子 Service（用于单一数据源查询）
stock_service = data_manager.get_data_service('stock_related.stock')
kline = stock_service.load_kline(...)
```

---

## 实施计划

### Phase 1: 重构目录结构 ✅ （当前）

- [x] 创建 3 个大类文件夹
- [x] 移动现有 Service 到对应位置
- [x] 创建大类 `__init__.py`（暂时只是转发器）

### Phase 2: 补全基础 Service

- [ ] 实现 `CorporateFinanceDataService`（财务数据）
- [ ] 实现 `InvestmentDataService`（投资记录）
- [ ] 实现 `IndustryDataService`（行业数据，可选）

### Phase 3: 配置驱动接口

- [ ] 在 `DataManager` 中实现 `resolve_data_requirements()`
- [ ] 支持两级访问：`'stock_related'` 和 `'stock_related.stock'`
- [ ] 更新 `DataManager._init_data_services()` 注册逻辑

### Phase 4: 集成到 Simulator（延后）

- [ ] 用 `resolve_data_requirements()` 替换现有的数据分发逻辑
- [ ] 验证缓存机制正常工作
- [ ] 性能测试

### Phase 5: 预设组合优化（可选，按需）

- [ ] 监控高频查询组合
- [ ] 针对性地添加 JOIN 优化
- [ ] 性能对比测试

---

## 数据查询流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        Strategy Settings                         │
│  data_requirements = {                                          │
│      'stock_kline': {...},                                      │
│      'corporate_finance': {...},                                │
│      'macro_economy': {...}                                     │
│  }                                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              DataManager.resolve_data_requirements()            │
│                                                                 │
│  1. 检查是否命中预设组合（可选优化）                              │
│  2. 没有预设，就分别查询                                         │
│  3. 返回数据字典                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ stock_      │ │ macro_      │ │ ui_transit  │
│ related     │ │ system      │ │             │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Stock       │ │ Macro       │ │ Investment  │
│ DataService │ │ DataService │ │ DataService │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┴───────────────┘
                       │
                       ▼
               ┌─────────────┐
               │   Models    │
               │ (Base       │
               │  Tables)    │
               └─────────────┘
```

---

## 性能考虑

### 当前性能保证

1. **Simulator 缓存**：每只股票的数据只查询一次
2. **宏观数据共享**：全局缓存，所有股票共用
3. **Model 层连接池**：数据库连接复用

### 未来优化方向（按需）

1. **预设组合**：针对高频组合添加 JOIN 查询
2. **批量加载**：一次性加载多只股票的数据
3. **延迟加载**：只在真正使用时才查询
4. **查询计划**：分析配置，生成最优查询策略

**原则：先保证正确性和简洁性，再谈性能优化。**

---

## 对贡献者的指导

### 添加新的 DataService

1. **确定大类**：股票相关 / 宏观系统 / UI中转
2. **创建子文件夹**：`<category>/<domain>/`
3. **实现 Service 类**：继承 `BaseDataService`
4. **在大类 `__init__.py` 中注册**
5. **在 `DataManager` 中注册**

### 添加预设组合（可选）

1. **确认高频使用**：通过监控或性能分析
2. **在大类 Service 中添加方法**：如 `load_xxx_with_yyy()`
3. **在 `resolve_data_requirements()` 中识别组合**
4. **性能对比测试**：确保优化有效

### 命名规范

- **加载方法**：`load_xxx()`
- **保存方法**：`save_xxx()`
- **组合方法**：`load_xxx_with_yyy()`
- **快照方法**：`load_xxx_snapshot()`

---

## 设计理念总结

1. **配置驱动**：策略作者只需声明需求，不关心实现
2. **简洁优先**：代码易读易维护，性能依赖缓存
3. **领域聚焦**：每个 Service 只负责一个业务领域
4. **渐进优化**：先实现功能，再针对性优化
5. **对开发者友好**：清晰的分类和文档，便于贡献

---

**最后更新：** 2025-12-05
**维护者：** @garnet

