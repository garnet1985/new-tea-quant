# Tushare Data Renewer 框架文档

## 📖 概述

BaseRenewer 是一个灵活、可扩展的数据更新框架，支持配置驱动的数据拉取、字段映射和保存。

### 核心设计原则

1. **基类简单通用** - 默认实现覆盖80%的常规场景
2. **职责清晰分离** - 每个方法职责单一明确
3. **API级别映射** - 字段映射在API返回后立即执行
4. **统一的处理入口** - 单个方法处理所有数据准备工作

---

## 🔄 完整数据流程

```
renew(latest_market_open_day, stock_list)
  ↓
should_renew() → 返回 jobs: List[Dict]
  ↓
对每个job:
  ↓
_request_apis(job)
  ├─ for each api:
  │   ├─ _request_single_api(job, api)
  │   │   ├─ 调用 API
  │   │   └─ map_api_data(data, api) ✨ 立即映射
  │   │       ├─ 输入：原始API数据（所有字段，API字段名）
  │   │       ├─ 默认：应用 api['mapping']
  │   │       └─ 输出：映射后数据（DB字段名）
  │   └─ 返回：已映射的数据
  └─ 返回：api_results {api_name: mapped_data}
  ↓
prepare_data_for_save(api_results) ✨
  ├─ 输入：已映射的API结果（DB字段名）
  ├─ 职责：合并 + 计算 + 清洗 + 验证
  ├─ 默认：单API直接返回，多API简单拼接
  └─ 输出：准备好保存的数据（DB字段名）
  ↓
_save_data(data)
```

---

## 🎣 子类可重写的核心钩子

### 1. `map_api_data(data, api)` - 映射单个API ⭐⭐⭐

**时机：** API返回后立即调用  
**用途：** 在字段映射前访问和处理原始字段

```python
def map_api_data(self, data, api):
    """针对特定API自定义映射"""
    api_name = api.get('name')
    
    if api_name == 'price':
        import pandas as pd
        df = pd.DataFrame(data)
        
        # 使用原始字段（可能未在mapping中配置）
        df['market_cap'] = df['close'] * df['total_share']
        df['pe_ttm'] = df['pe']
        
        # 应用配置的mapping
        return self.apply_single_api_mapping(df, api['mapping'])
    
    # 其他API使用默认行为
    return super().map_api_data(data, api)
```

**何时使用：**
- ✅ 需要访问API原始字段（包括未映射的字段）
- ✅ 需要在单个API内计算衍生字段
- ✅ 需要特殊的数据预处理

---

### 2. `prepare_data_for_save(api_results, job=None)` - 准备保存数据 ⭐⭐⭐⭐⭐

**时机：** 所有API调用和映射完成后  
**用途：** 统一处理所有数据准备工作（合并、清洗、计算、验证）

**参数：**
- `api_results`: 已映射的API结果字典
- `job`: 当前任务信息（可选，包含start_date, end_date, ts_code, term等字段）

```python
# ===== 场景1: 单API + 数据清洗 =====
def prepare_data_for_save(self, api_results, job=None):
    """处理单个API的数据"""
    data = list(api_results.values())[0]
    
    import pandas as pd
    df = pd.DataFrame(data)
    
    # 数据清洗
    df = df[df['price'] > 0]
    df = df.drop_duplicates(subset=['id', 'date'])
    
    return df

# ===== 场景2: 多API + 合并 + 计算 =====
def prepare_data_for_save(self, api_results):
    """合并多个API并计算"""
    import pandas as pd
    
    # 合并多个API（使用DB字段名）
    df_price = pd.DataFrame(api_results['price'])
    df_volume = pd.DataFrame(api_results['volume'])
    merged = pd.merge(df_price, df_volume, on=['date', 'id'])
    
    # 计算跨API的衍生字段
    merged['total_value'] = merged['close'] * merged['volume']
    
    # 数据清洗
    merged = merged.dropna()
    
    return merged

# ===== 场景3: 使用默认合并 + 自定义处理 =====
def prepare_data_for_save(self, api_results):
    """使用基类的默认合并"""
    # 使用基类的默认合并
    data = self.default_merge_api_results(api_results)
    
    # 自定义处理
    import pandas as pd
    df = pd.DataFrame(data)
    df['processed'] = df['raw'] * 100
    
    return df
```

**何时使用：**
- ✅ 单API场景的数据清洗
- ✅ 多API的JOIN合并
- ✅ 跨API的衍生字段计算
- ✅ 数据验证和过滤
- ✅ 业务逻辑处理

---

### 3. `build_jobs(latest_market_open_day, stock_list, db_records)` - 构建任务 ⭐⭐

**用途：** 自定义任务构建逻辑

```python
def build_jobs(self, latest_market_open_day, stock_list=None, db_records=None):
    """自定义任务构建"""
    # 例如：股票列表不需要按股票分任务
    return [{
        'start_date': '20000101',
        'end_date': latest_market_open_day
    }]
```

---

### 4. `should_renew(latest_market_open_day, stock_list)` - 判断是否更新 ⭐

**用途：** 自定义更新判断逻辑（通常不需要重写）

---

## 🛠️ 辅助工具方法（供子类使用）

```python
# 数据格式转换
self.to_records(data)     # 转为 list[dict]
self.to_df(data)          # 转为 DataFrame

# 字段映射
self.apply_single_api_mapping(data, mapping)  # 应用单个API的mapping
self.default_merge_api_results(api_results)    # 使用默认合并逻辑
```

---

## 📋 配置格式

```python
CONFIG = {
    'table_name': 'stock_klines',
    'job_mode': 'multithread',  # 'simple' or 'multithread'
    'renew_mode': 'incremental',  # 'incremental', 'upsert', 'overwrite'
    
    'date': {
        'field': 'date',
        'type': 'date',  # 'date' or 'quarter'
        'interval': 'day'  # 'day', 'week', 'month', 'quarter'
    },
    
    'multithread': {
        'workers': 10  # 工作线程数
    },
    
    'rate_limit': {
        'max_per_minute': 800  # API限流
    },
    
    'apis': [
        {
            'name': 'daily',  # API名称
            'method': 'daily',  # API方法名
            'params': {  # API参数（支持变量替换）
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            },
            'mapping': {  # 字段映射
                # 简单映射: db_field: api_field
                'id': 'ts_code',
                'date': 'trade_date',
                'open': 'open',
                'close': 'close',
                
                # 带转换的映射
                'volume': {
                    'source': 'vol',
                    'transform': lambda x: int(x * 100) if x else 0
                },
                
                # 使用整个record的lambda
                'full_code': lambda r: f"{r.get('ts_code', '')}.{r.get('exchange', '')}",
                
                # 常量值
                'data_source': {
                    'value': 'tushare'
                },
                
                # 带默认值
                'adj_factor': {
                    'source': 'adj_factor',
                    'default': 1.0
                }
            }
        }
    ]
}
```

---

## 📝 字段映射详解

### 支持的映射类型

#### 1. 简单字符串映射
```python
'mapping': {
    'id': 'ts_code',  # DB字段: API字段
    'date': 'trade_date'
}
```

#### 2. 带转换函数
```python
'mapping': {
    'volume': {
        'source': 'vol',
        'transform': lambda x: int(x * 100) if x else 0
    }
}
```

#### 3. 使用整个record的lambda
```python
'mapping': {
    # lambda接收整个record，可访问多个字段
    'full_name': lambda r: f"{r.get('first_name', '')} {r.get('last_name', '')}",
    'total_value': lambda r: r.get('price', 0) * r.get('volume', 0)
}
```

#### 4. 常量值
```python
'mapping': {
    'data_source': {
        'value': 'tushare'
    }
}
```

#### 5. 带默认值
```python
'mapping': {
    'adj_factor': {
        'source': 'adj_factor',
        'default': 1.0  # API未返回时使用
    }
}
```

---

## 🎨 完整使用示例

### 示例1: 简单场景（默认行为）

```python
# ============ config.py ============
CONFIG = {
    'table_name': 'gdp',
    'job_mode': 'simple',
    'renew_mode': 'incremental',
    'apis': [{
        'name': 'gdp',
        'method': 'cn_gdp',
        'mapping': {
            'quarter': 'quarter',
            'gdp': 'gdp',
            'gdp_yoy': 'gdp_yoy'
        }
    }]
}

# ============ renewer.py ============
class GDPRenewer(BaseRenewer):
    pass  # 不需要任何重写！
```

---

### 示例2: 单API + 数据处理

```python
# ============ config.py ============
CONFIG = {
    'table_name': 'stock_list',
    'apis': [{
        'name': 'stock_basic',
        'method': 'stock_basic',
        'mapping': {
            'ts_code': 'ts_code',
            'name': 'name',
            'market': 'market',
            'list_date': 'list_date'
        }
    }]
}

# ============ renewer.py ============
class StockListRenewer(BaseRenewer):
    
    def prepare_data_for_save(self, api_results):
        """过滤北交所股票"""
        import pandas as pd
        
        data = list(api_results.values())[0]
        df = pd.DataFrame(data)
        
        # 数据清洗：排除北交所
        df = df[df['market'] != 'BJ']
        
        # 去重
        df = df.drop_duplicates(subset=['ts_code'])
        
        return df
```

---

### 示例3: 多API + 复杂处理

```python
# ============ config.py ============
CONFIG = {
    'table_name': 'stock_klines',
    'job_mode': 'multithread',
    'apis': [
        {
            'name': 'daily',
            'method': 'daily',
            'mapping': {
                'id': 'ts_code',
                'date': 'trade_date',
                'open': 'open',
                'close': 'close',
                'volume': 'vol'
            }
        },
        {
            'name': 'adj',
            'method': 'adj_factor',
            'mapping': {
                'id': 'ts_code',
                'date': 'trade_date',
                'adj_factor': 'adj_factor'
            }
        }
    ]
}

# ============ renewer.py ============
class StockKlineRenewer(BaseRenewer):
    
    def map_api_data(self, data, api):
        """处理daily API的原始数据"""
        api_name = api.get('name')
        
        if api_name == 'daily':
            import pandas as pd
            df = pd.DataFrame(data)
            
            # 使用API返回的未映射字段计算
            if 'total_share' in df.columns:
                df['market_cap'] = df['close'] * df['total_share']
            
            # 应用mapping
            return self.apply_single_api_mapping(df, api['mapping'])
        
        return super().map_api_data(data, api)
    
    def prepare_data_for_save(self, api_results):
        """合并daily和adj数据"""
        import pandas as pd
        
        df_daily = pd.DataFrame(api_results['daily'])
        df_adj = pd.DataFrame(api_results['adj'])
        
        # JOIN合并
        merged = pd.merge(df_daily, df_adj, on=['date', 'id'], how='left')
        
        # 计算复权价格
        merged['adj_open'] = merged['open'] * merged['adj_factor'].fillna(1.0)
        merged['adj_close'] = merged['close'] * merged['adj_factor'].fillna(1.0)
        
        # 数据清洗
        merged = merged[merged['close'] > 0]
        merged = merged.drop_duplicates(subset=['id', 'date'])
        
        return merged
```

---

## 🔧 子类可重写方法清单

### 必须了解的核心方法

| 方法 | 职责 | 重写频率 | 优先级 |
|------|------|---------|--------|
| `prepare_data_for_save(api_results)` | 准备保存数据 | ⭐⭐⭐⭐⭐ | 最高 |
| `map_api_data(data, api)` | 映射单个API | ⭐⭐⭐ | 中 |
| `build_jobs(...)` | 构建任务列表 | ⭐⭐ | 低 |
| `should_renew(...)` | 判断是否更新 | ⭐ | 很低 |

### 可选的辅助方法

| 方法 | 用途 | 说明 |
|------|------|------|
| `should_execute_api(api, results)` | 判断是否执行API | 处理API依赖 |
| `prepare_api_params(api, job)` | 准备API参数 | 复杂参数逻辑 |
| `get_renew_mode()` | 获取更新模式 | 动态决定模式 |

### 辅助工具方法（供子类调用）

| 方法 | 用途 |
|------|------|
| `to_records(data)` | 转换为 list[dict] |
| `to_df(data)` | 转换为 DataFrame |
| `apply_single_api_mapping(data, mapping)` | 应用单个API的mapping配置 |
| `default_merge_api_results(api_results)` | 使用默认合并逻辑 |

---

## 📊 配置详解

### 更新模式 (renew_mode)

| 模式 | 行为 | 使用场景 |
|------|------|----------|
| `incremental` | 增量更新，只拉取新数据 | 日常更新 |
| `upsert` | 覆盖式更新 | 数据可能有修正 |
| `overwrite` | 清空后全量更新 | 数据重建 |

### 作业模式 (job_mode)

| 模式 | 行为 | 使用场景 |
|------|------|----------|
| `simple` | 顺序执行 | 宏观数据、单任务 |
| `multithread` | 并发执行 | 股票数据、多任务 |

### 时间间隔 (interval)

| 间隔 | 说明 | 使用场景 |
|------|------|----------|
| `day` | 日级别 | 日K线 |
| `week` | 周级别 | 周K线 |
| `month` | 月级别 | 月度数据 |
| `quarter` | 季度级别 | 财务数据 |

---

## 💡 最佳实践

### 1. 配置优先
- 尽量通过配置实现功能，减少代码重写
- 显式声明所有需要保存的字段

### 2. 职责分离
- **单API内的计算** → `map_api_data`
- **跨API的计算** → `prepare_data_for_save`
- **业务逻辑处理** → `prepare_data_for_save`

### 3. 使用辅助方法
```python
# ✅ 推荐：使用辅助方法
def prepare_data_for_save(self, api_results):
    data = self.default_merge_api_results(api_results)
    df = self.to_df(data)
    # 处理...
    return df

# ❌ 不推荐：重复实现转换逻辑
def prepare_data_for_save(self, api_results):
    data = []
    for result in api_results.values():
        if isinstance(result, list):
            data.extend(result)
        elif hasattr(result, 'to_dict'):
            data.extend(result.to_dict('records'))
    # ...
```

### 4. 保持方法简洁
- 如果方法超过50行，考虑拆分为私有辅助方法
- 使用有意义的变量名

---

## 🚀 快速开始

### 步骤1: 创建配置文件

```python
# renewers/my_renewer/config.py
CONFIG = {
    'table_name': 'my_table',
    'job_mode': 'simple',
    'renew_mode': 'incremental',
    'date': {
        'field': 'date',
        'type': 'date',
        'interval': 'day'
    },
    'apis': [{
        'name': 'my_api',
        'method': 'get_data',
        'params': {
            'start_date': '{start_date}',
            'end_date': '{end_date}'
        },
        'mapping': {
            'id': 'code',
            'date': 'trade_date',
            'value': 'data_value'
        }
    }]
}
```

### 步骤2: 创建Renewer类（可选）

```python
# renewers/my_renewer/renewer.py
from app.data_source.providers.tushare.base_renewer import BaseRenewer

class MyRenewer(BaseRenewer):
    # 如果默认行为足够，不需要重写任何方法
    pass

# 或者重写需要的方法
class MyRenewer(BaseRenewer):
    def prepare_data_for_save(self, api_results):
        data = list(api_results.values())[0]
        # 自定义处理
        return self._process(data)
```

### 步骤3: 注册到main.py

```python
# main.py
from .renewers.my_renewer.config import CONFIG
from .renewers.my_renewer.renewer import MyRenewer

self.my_renewer = MyRenewer(self.db, self.api, self.storage, CONFIG)
```

---

## ⚠️ 常见问题

### Q1: 字段名相同也需要配置mapping吗？
**A:** 是的。显式配置让配置成为文档，一目了然。

### Q2: 多个API有相同字段怎么办？
**A:** 在mapping中映射到不同的DB字段名：
```python
'apis': [
    {'mapping': {'raw_price': 'price'}},  # API1的price
    {'mapping': {'adj_price': 'price'}}   # API2的price
]
```

### Q3: 只需要API返回字段的一部分怎么办？
**A:** mapping配置即白名单，只配置需要的字段即可。

### Q4: 何时重写 `map_api_data`，何时重写 `prepare_data_for_save`？
**A:** 
- 需要访问原始字段做计算 → `map_api_data`
- 需要合并多个API或数据清洗 → `prepare_data_for_save`
- 两者可以同时重写

---

## 📋 NaN/NULL 处理

### 默认行为

**无需任何配置**，框架会自动从表schema获取字段类型，并根据类型处理NaN：

| 字段类型 | NaN → 默认值 | 示例 |
|---------|-------------|------|
| float, double, decimal | 0 | price: NaN → 0.0 |
| int, bigint, tinyint | 0 | volume: NaN → 0 |
| varchar, text | '' (空字符串) | name: NaN → '' |
| datetime, date | None | date: NaN → None |

**目的：** 确保所有表中不出现NaN/NULL，避免数据库错误。

### 扩展配置

如果需要特殊处理，可以在config中添加 `nan_handling` 配置：

#### 场景1: 关闭自动转换（保留所有NaN为NULL）

```python
CONFIG = {
    'nan_handling': {
        'auto_convert': False  # 关闭自动转换
    }
}
```

#### 场景2: 指定某些字段允许NULL

```python
CONFIG = {
    'nan_handling': {
        'allow_null_fields': ['optional_indicator', 'beta', 'alpha']
    }
}
```

#### 场景3: 自定义字段的默认值

```python
CONFIG = {
    'nan_handling': {
        'field_defaults': {
            'risk_score': -1,
            'grade': 'unrated'
        }
    }
}
```

### 处理优先级

```
1. field_defaults (最高优先级)
   ↓ 如果字段在field_defaults中，使用自定义值
   
2. allow_null_fields
   ↓ 如果字段在allow_null_fields中，保留None
   
3. schema类型 (默认行为)
   ↓ 根据字段类型自动决定
```

---

## 📊 多线程日志配置

### 默认日志

不配置时使用默认格式：
```
000001.SZ (平安银行) 更新完毕 - 进度: 3.3%
```

### 自定义日志模板

```python
CONFIG = {
    'multithread': {
        'workers': 6,  # 可选，默认4
        'log': {
            'success': '✅ 股票 {stock_name} {id} [{term}] 更新完毕 - 进度 {progress}%',
            'failure': '❌ 股票 {stock_name} {id} [{term}] 更新失败'
        }
    }
}
```

### 可用变量

- **内置变量**: `progress` (数字，不含%符号), `table_name`
- **job字段**: job中所有非下划线开头的字段（如 `id`, `ts_code`, `term`, `start_date`, `end_date`）
- **自定义变量**: 在`build_jobs`中通过`_log_vars`添加

### 在build_jobs中添加日志变量

```python
def build_jobs(self, ...):
    jobs.append({
        'id': stock_id,
        'term': 'daily',
        '_log_vars': {  # 自定义日志变量
            'stock_name': stock.get('name'),
            'market': stock.get('market')
        }
    })
```

### 完全自定义日志

子类可以重写`log_job_completion`方法：

```python
class MyRenewer(BaseRenewer):
    def log_job_completion(self, job: Dict, is_success: bool, progress_percent: float):
        """完全自定义日志"""
        if is_success and progress_percent >= 100:
            logger.success("🎉 所有任务完成！")
        else:
            # 使用默认格式
            self.log_default(job, is_success, progress_percent)
```

---

## ⚡ 限流配置

### Buffer设计

```python
CONFIG = {
    'rate_limit': {
        'max_per_minute': 800  # 供应商限流
    }
}
```

**Buffer自动计算：**
- 简单模式: `buffer = 5`
- 多线程模式: `buffer = workers + 5`

**原理：**
- 当触发限流时，可能有N个worker的请求正在路上
- Buffer = worker数 + 安全余量

**实际限流：**
```
6 workers, 800次/分钟限流:
  → buffer = 6 + 5 = 11
  → 实际限流 = 800 - 11 = 789次/分钟
  → 利用率 = 98.6% 🚀
```

---

## 📚 相关文档

- `base_renewer.py` - 框架源码
- `renewers/stock_kline/` - Stock K-line实现示例

