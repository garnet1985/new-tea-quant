# 基础类设计文档

## 📋 概览

本文档详细说明 `BaseProvider` 和 `BaseHandler` 两个基础类的设计。

---

## 🏗️ BaseProvider（基础设施层）

### 设计原则

1. **纯 API 封装** - 不包含业务逻辑
2. **声明式元数据** - 限流、认证信息作为类属性
3. **简单可测试** - 每个方法只做一件事

### 职责

- ✅ 封装第三方 API 调用
- ✅ 声明 API 限流信息（不执行）
- ✅ 认证配置和验证
- ✅ 错误转换（统一错误格式）
- ❌ 不包含业务逻辑
- ❌ 不执行限流逻辑
- ❌ 不处理数据标准化

### 类结构

```python
class BaseProvider(ABC):
    # 类属性（元信息）
    provider_name: str              # Provider 名称
    requires_auth: bool             # 是否需要认证
    auth_type: str                  # 认证类型
    api_limits: Dict[str, int]      # API 限流声明
    default_rate_limit: int         # 默认限流
    
    # 方法
    __init__(config)                # 初始化
    _initialize()                   # 子类实现
    get_api_limit(api_name)         # 获取限流信息
    get_metadata()                  # 获取元信息
    handle_error(error, api_name)   # 错误处理
```

### 使用示例

```python
class TushareProvider(BaseProvider):
    provider_name = "tushare"
    requires_auth = True
    auth_type = "token"
    
    api_limits = {
        "get_daily_kline": 100,
        "get_weekly_kline": 50,
    }
    
    def _initialize(self):
        self.api = ts.pro_api(self.config['token'])
    
    def get_daily_kline(self, ts_code, start_date, end_date):
        try:
            return self.api.daily(ts_code=ts_code, ...)
        except Exception as e:
            raise self.handle_error(e, "get_daily_kline")
```

---

## 🎯 BaseHandler（业务逻辑层）

### 设计原则

1. **fetch + normalize 分离** - 职责清晰
2. **模板方法模式** - 统一流程，灵活扩展
3. **元信息自描述** - 类属性声明特性

### 职责

- ✅ 调用 Provider 获取数据
- ✅ 数据标准化（转为 schema 格式）
- ✅ 多 Provider 组合
- ✅ 依赖数据处理
- ✅ 批量处理逻辑
- ❌ 不包含多线程调度（由 Manager 负责）
- ❌ 不包含全局限流管理（由 Manager 负责）

### 类结构

```python
class BaseHandler(ABC):
    # 类属性（元信息）
    data_source: str                # 数据源名称
    renew_type: str                 # "refresh" | "incremental"
    description: str                # 描述
    dependencies: List[str]         # 依赖
    
    # 核心方法
    __init__(schema, params)        # 初始化
    fetch(context)                  # 获取原始数据（子类实现）
    normalize(raw_data)             # 标准化（子类实现）
    fetch_and_normalize(context)    # 完整流程（模板方法）
    
    # 钩子方法
    before_fetch(context)
    after_fetch(raw_data, context)
    before_normalize(raw_data)
    after_normalize(normalized_data)
    on_error(error, context)
    
    # 辅助方法
    validate(data)                  # 数据验证
    register_provider(name, provider)
    get_provider(name)
    get_metadata()
    get_param(key, default)
```

### 执行流程

```
fetch_and_normalize()
    ↓
before_fetch()
    ↓
fetch()  ← 子类实现
    ↓
after_fetch()
    ↓
before_normalize()
    ↓
normalize()  ← 子类实现
    ↓
after_normalize()
    ↓
validate()
    ↓
return normalized_data
```

### 使用示例

```python
class TushareStockListHandler(BaseHandler):
    data_source = "stock_list"
    renew_type = "refresh"
    description = "从 Tushare 获取股票列表"
    dependencies = []
    
    def __init__(self, schema, params=None):
        super().__init__(schema, params)
        self.tushare = TushareProvider()
        self.register_provider("tushare", self.tushare)
    
    async def fetch(self, context):
        provider = self.get_provider("tushare")
        return provider.get_stock_list()
    
    async def normalize(self, raw_data):
        return {
            "stocks": [
                {"ts_code": row["ts_code"], "name": row["name"]}
                for row in raw_data
            ]
        }
```

---

## 🔄 职责总结

| 层次 | 类 | 主要职责 | 关键特性 |
|-----|---|----------|---------|
| **基础设施** | BaseProvider | API 封装 + 元数据声明 | 简单、纯粹、可测试 |
| **业务逻辑** | BaseHandler | 数据获取 + 标准化 | 灵活、可扩展、可组合 |
| **协调管理** | DataSourceManager | 全局调度 + 限流执行 | 统一、高效、可追踪 |

---

## 📝 设计优势

1. **职责清晰** - 每层各司其职
2. **易于测试** - Provider 和 Handler 可独立测试
3. **灵活扩展** - 钩子方法提供扩展点
4. **声明式** - 元信息作为类属性，易于发现
5. **统一管理** - 限流在 Manager 层统一执行

