# Data Type 管理机制

## 核心概念

**Data Type 不是硬编码的，而是由 Provider 动态声明的！**

---

## ❌ 误解：Data Type 是固定的

```python
# ❌ 错误理解：以为Coordinator里硬编码了data_type列表
class DataCoordinator:
    SUPPORTED_DATA_TYPES = [  # ❌ 不存在这种硬编码
        'stock_kline',
        'adj_factor',
        'gdp'
    ]
```

---

## ✅ 正确：Data Type 是动态注册的

### 1. Provider 声明自己提供什么

```python
# Provider只需要在get_provider_info()中声明
class TushareAdapter(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="tushare",
            provides=[  # ✅ 动态声明
                "stock_list",
                "stock_kline",
                "corporate_finance",
                "gdp",
                "price_indexes",
                "shibor",
                "lpr",
                "stock_index_indicator",
                "stock_index_indicator_weight",
                "industry_capital_flow"
            ]
        )

class AKShareAdapter(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="akshare",
            provides=[  # ✅ 动态声明
                "adj_factor"
            ]
        )
```

### 2. Registry 自动建立索引

```python
class ProviderRegistry:
    def __init__(self):
        self._providers = {}
        self._data_type_index = {}  # ✅ 自动构建的索引
    
    def mount(self, name: str, provider: BaseProvider):
        """挂载Provider时自动注册data_type"""
        info = provider.get_provider_info()
        
        # 自动更新索引
        for data_type in info.provides:
            if data_type not in self._data_type_index:
                self._data_type_index[data_type] = []
            self._data_type_index[data_type].append(name)
        
        # ✅ 结果：_data_type_index = {
        #     'stock_kline': ['tushare'],
        #     'adj_factor': ['akshare'],
        #     'gdp': ['tushare'],
        #     ...
        # }
    
    def get_providers_for(self, data_type: str) -> List[str]:
        """查询支持某data_type的Provider（动态查询）"""
        return self._data_type_index.get(data_type, [])
```

### 3. Coordinator 动态查询

```python
class DataCoordinator:
    async def coordinate_update(self, data_type: str, end_date: str):
        """更新指定数据类型（不需要硬编码）"""
        
        # ✅ 动态查询：哪个Provider支持这个data_type？
        providers = self.registry.get_providers_for(data_type)
        
        if not providers:
            raise ValueError(f"没有Provider支持数据类型: {data_type}")
        
        provider_name = providers[0]
        provider = self.registry.get(provider_name)
        
        # 执行更新
        await provider.renew_data_type(data_type, end_date, context)
```

---

## 🚀 新增 Data Type 的完整流程

### 场景：新增 "financial_news" 数据类型

#### Step 1: 实现 Provider（只需声明）

```python
class WindProvider(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            name="wind",
            provides=[
                "financial_news",      # ✅ 新增data_type
                "analyst_rating"       # ✅ 再新增一个
            ],
            dependencies=[
                Dependency(
                    provider="tushare",
                    data_types=["stock_list"]
                )
            ]
        )
    
    async def renew_all(self, end_date, context):
        """实现更新逻辑"""
        stock_list = context.stock_list
        
        # 更新财经新闻
        await self._update_financial_news(end_date, stock_list)
        
        # 更新分析师评级
        await self._update_analyst_rating(end_date, stock_list)
    
    async def renew_data_type(self, data_type, end_date, context):
        """支持单独更新某个类型"""
        stock_list = context.stock_list
        
        if data_type == "financial_news":
            await self._update_financial_news(end_date, stock_list)
        elif data_type == "analyst_rating":
            await self._update_analyst_rating(end_date, stock_list)
```

#### Step 2: 挂载 Provider（一行代码）

```python
# 在 DataSourceManager 初始化时
registry.mount('wind', WindProvider(data_manager))

# ✅ 自动发生：
# _data_type_index['financial_news'] = ['wind']
# _data_type_index['analyst_rating'] = ['wind']
```

#### Step 3: 使用（直接调用）

```python
# ✅ 立即可用，无需任何配置
await data_source.renew_data_type('financial_news', '20250101')

# ✅ Coordinator自动：
# 1. 查询：哪个Provider支持financial_news？ → wind
# 2. 检查：wind的依赖是否满足？ → stock_list
# 3. 执行：wind.renew_data_type('financial_news', ...)
```

---

## 📋 目前设计中的所有 Data Type

### 1. Tushare 提供的 Data Type（10个）

```python
TUSHARE_DATA_TYPES = [
    # 基础数据
    "stock_list",                      # 股票列表
    "stock_kline",                     # 股票K线（日线）
    
    # 企业财务
    "corporate_finance",               # 企业财务数据（季报）
    
    # 宏观经济
    "gdp",                            # GDP（季度）
    "price_indexes",                  # CPI/PPI/PMI（月度）
    "shibor",                         # 上海银行间同业拆放利率（日度）
    "lpr",                            # 贷款市场报价利率（月度）
    
    # 指数数据
    "stock_index_indicator",          # 指数指标
    "stock_index_indicator_weight",   # 指数权重
    
    # 资金流向
    "industry_capital_flow"           # 行业资金流向
]
```

### 2. AKShare 提供的 Data Type（1个）

```python
AKSHARE_DATA_TYPES = [
    "adj_factor"                      # 复权因子（日度）
]
```

### 3. 未来可能新增的 Data Type（示例）

```python
# Wind Provider
WIND_DATA_TYPES = [
    "financial_news",                 # 财经新闻
    "analyst_rating",                 # 分析师评级
    "company_announcement"            # 公司公告
]

# Choice Provider
CHOICE_DATA_TYPES = [
    "institutional_holdings",         # 机构持仓
    "fund_flow",                      # 资金流向
    "margin_trading"                  # 融资融券
]

# 自定义Provider
CUSTOM_DATA_TYPES = [
    "social_media_sentiment",         # 社交媒体情绪
    "alternative_data"                # 另类数据
]
```

---

## 🔥 Data Type 的命名规范

### 推荐格式

```python
# 格式：<主体>_<类型>_<频率>（可选）
"stock_kline"           # 股票K线
"stock_kline_weekly"    # 股票周K线（如果新增）
"corporate_finance"     # 企业财务
"macro_gdp"            # 宏观GDP
"index_weight"         # 指数权重
```

### 映射到表名（配置）

```python
# config/data_source.yaml

data_type_mapping:
  # data_type → table_name（可以不同）
  stock_kline: stock_kline
  adj_factor: adj_factor
  corporate_finance: corporate_finance
  price_indexes: 
    - cpi
    - ppi  
    - pmi
  gdp: gdp
  shibor: shibor
  lpr: lpr
  stock_index_indicator: stock_index_indicator
  stock_index_indicator_weight: stock_index_indicator_weight
  industry_capital_flow: industry_capital_flow
  
  # 新增
  financial_news: financial_news
  analyst_rating: analyst_rating
```

---

## 🎯 完整的 Data Type 生命周期

### 1. 声明（Provider中）

```python
class Provider:
    def get_provider_info(self):
        return ProviderInfo(
            provides=["new_data_type"]  # ✅ 声明
        )
```

### 2. 注册（Registry自动）

```python
# 挂载时自动注册
registry.mount('provider_name', Provider())
# → _data_type_index['new_data_type'] = ['provider_name']
```

### 3. 查询（Coordinator动态）

```python
# 查询支持的Provider
providers = registry.get_providers_for('new_data_type')
# → ['provider_name']
```

### 4. 使用（用户代码）

```python
# 直接使用，无需配置
await data_source.renew_data_type('new_data_type', end_date)
```

---

## 💡 Data Type vs Table Name

### 区别

```python
# Data Type：业务概念（抽象）
data_type = "stock_kline"

# Table Name：数据库表名（具体）
table_name = "stock_kline"  # 可以相同，也可以不同

# 另一个例子：
data_type = "price_indexes"  # 一个业务概念
table_names = ["cpi", "ppi", "pmi"]  # 多个数据库表
```

### 映射关系（在配置中）

```python
# Provider中只关心业务概念
def renew_data_type(self, data_type, end_date, context):
    if data_type == "price_indexes":
        # 更新多个表
        self.cpi_renewer.renew(end_date)
        self.ppi_renewer.renew(end_date)
        self.pmi_renewer.renew(end_date)

# Coordinator中需要映射（可选配置）
def _is_data_available(self, data_type, end_date):
    # 映射到表名
    tables = self._get_tables_for_data_type(data_type)
    # tables = ['cpi', 'ppi', 'pmi']
    
    # 检查所有表
    for table in tables:
        if not self._check_table_updated(table, end_date):
            return False
    return True
```

---

## 🔄 动态注册的优势

### 1. 可扩展性

```python
# ✅ 新增data_type只需要实现Provider
# ❌ 不需要修改Coordinator
# ❌ 不需要修改Registry
# ❌ 不需要修改配置文件（可选）
```

### 2. 解耦性

```python
# Provider只关心自己提供什么
# Coordinator只关心如何协调
# Registry只关心如何索引
# 三者完全解耦
```

### 3. 测试性

```python
# Mock Provider可以声明任意data_type
class MockProvider(BaseProvider):
    def get_provider_info(self):
        return ProviderInfo(
            provides=["test_data_type"]  # 测试用
        )

# 立即可用
registry.mount('mock', MockProvider())
await coordinator.coordinate_update('test_data_type', '20250101')
```

---

## 📊 Data Type 注册表（自动生成）

Coordinator可以提供查询方法：

```python
class DataCoordinator:
    def list_all_data_types(self) -> List[str]:
        """列出所有支持的data_type"""
        return list(self.registry._data_type_index.keys())
    
    def get_data_type_info(self, data_type: str) -> Dict:
        """获取data_type的详细信息"""
        providers = self.registry.get_providers_for(data_type)
        
        info = {
            'data_type': data_type,
            'providers': []
        }
        
        for provider_name in providers:
            metadata = self.registry.get_metadata(provider_name)
            info['providers'].append({
                'name': provider_name,
                'dependencies': metadata.dependencies
            })
        
        return info

# 使用
all_types = coordinator.list_all_data_types()
print(all_types)
# ['stock_list', 'stock_kline', 'adj_factor', 'gdp', ...]

info = coordinator.get_data_type_info('adj_factor')
print(info)
# {
#     'data_type': 'adj_factor',
#     'providers': [
#         {
#             'name': 'akshare',
#             'dependencies': [
#                 Dependency(provider='tushare', data_types=['stock_kline'])
#             ]
#         }
#     ]
# }
```

---

## 🎯 总结

### 问题1：协调器的actions是固定的吗？

**答：不是！**
- Coordinator不知道有哪些data_type
- 它只负责查询Registry："谁能提供这个data_type？"
- Registry根据Provider的声明动态返回

### 问题2：新增provider或renew数据需要增加data_type吗？

**答：是的，但非常简单！**
- 在Provider的`get_provider_info()`中添加到`provides`列表
- Registry会自动注册
- 无需修改Coordinator代码
- 无需修改任何配置（可选）

### 问题3：目前有哪些data_type？

**答：11个（可动态扩展）**
- Tushare提供10个
- AKShare提供1个
- 未来可以无限扩展

### 核心设计思想

```
Provider声明 → Registry索引 → Coordinator查询 → 动态路由

完全解耦，完全动态，完全可扩展！
```

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

