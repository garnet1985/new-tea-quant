# Data Source 现有实现分析

## 目的

全面梳理现有 data_source 的功能和特殊处理，为新架构设计提供完整的需求清单。

---

## 🎯 核心功能清单

### 1. 数据更新模式（Renew Mode）

#### 1.1 三种更新模式
```python
- overwrite:    全量删除后插入
- incremental:  增量请求 + replace保存（内存占用小）
- upsert:       全量加载 + replace保存（适合全量对比）
```

#### 1.2 增量更新逻辑
- 查询数据库最新记录
- 计算需要更新的时间范围
- 构建增量任务列表
- **特殊处理**：
  - 新股票：全量拉取（从 `data_default_start_date` 开始）
  - 已有股票：增量拉取（从最新日期的下一个周期开始）

### 2. 时间周期处理

#### 2.1 支持的周期类型
```python
- day:      日度数据（K线、Shibor等）
- week:     周度数据
- month:    月度数据（LPR、Money Supply等）
- quarter:  季度数据（GDP、企业财务等）
```

#### 2.2 披露延迟处理 ⭐ 关键
```python
disclosure_delay_months: 1  # 财报披露延迟

# 逻辑：
# 当前日期 = 2025-10-15（Q4第一个月）
# 前一季度 = Q3（2025-09-30）
# 披露截止 = 2025-10-31
# 判断：当前 < 截止 → 往前推一个季度 → 返回 Q2
```

**场景**：企业财务数据在季度结束后需要1个月才能披露完整

#### 2.3 日期格式转换
```python
# 内部统一：YYYYMMDD（标准日期格式）
# API格式：可配置
  - date:    20250930
  - quarter: 2025Q3
  - month:   202509

# 关键方法：
_convert_to_api_format()  # 边界转换
DataSourceService.from_standard_date()
DataSourceService.to_standard_date()
```

### 3. 限流器（Rate Limiter）⭐ 核心

#### 3.1 多层级限流
```python
# 层级1：全局限流器管理器
RateLimiterManager:
    - 管理多个限流器实例
    - 每个数据类型独立限流
    - 支持运行时创建

# 层级2：单个限流器
APIRateLimiter:
    - max_per_minute: 200（每分钟最大请求）
    - buffer: workers + 5（多线程缓冲）
    - 令牌桶算法
```

#### 3.2 Buffer 设计原理 ⭐ 重要
```python
# 多线程场景：
# 触发限流时，可能有N个线程的请求正在路上
# buffer = workers + 5（激进配置，追求高性能）

# 简单模式：
# buffer = 5（固定，够用即可）
```

### 4. 多线程/多进程 ⭐ 核心

#### 4.1 工作模式
```python
job_mode:
    - simple:      单线程（宏观数据、少量任务）
    - multithread: 多线程（K线数据、大量任务）
    
multithread:
    workers: 4  # 线程数（默认4）
```

#### 4.2 线程安全机制
```python
# 1. 线程局部DB（每个线程独立连接）
self._thread_local = threading.local()
self._thread_dbs = []
self._thread_dbs_lock = threading.Lock()

# 2. 进度计数器加锁
self._progress_lock = threading.Lock()
self._completed_jobs = 0
self._total_jobs = len(jobs)

# 3. 限流器线程安全
rate_limiter.acquire()  # 内部加锁
```

#### 4.3 智能超时监控 ⭐ 特殊
```python
# 执行时间监控
if execution_time > 30:  # 超过30秒警告
    logger.warning(f"任务执行时间过长: {execution_time:.1f}秒")

# 智能超时机制
timeout=3600  # 全局超时
# 实际由智能机制控制单个任务
```

### 5. 进度跟踪（Progress Tracker）

#### 5.1 多层级进度
```python
# 层级1：任务级别
completed_jobs / total_jobs

# 层级2：详细日志
logger.info(f"{ts_code} ({stock_name}) 更新完毕 - 进度: 3.3%")

# 层级3：可配置日志模板
log:
    success: "{id} ({stock_name}) 完成 - {progress}%"
    failure: "{id} 失败"
```

#### 5.2 日志变量提取 ⭐ 灵活
```python
_log_vars:  # 由 build_jobs 设置
    stock_name: "平安银行"
    quarter: "2024Q1"

# 支持的变量：
- progress: 进度百分比
- id, ts_code: 标识符
- stock_name: 名称
- start_date, end_date: 日期
- 自定义变量
```

### 6. API 调用与字段映射

#### 6.1 多 API 支持
```python
apis:
    - name: "price"
      method: "daily"
      params: {ts_code: "{ts_code}", start_date: "{start_date}"}
      mapping: {...}
    
    - name: "volume"
      method: "stk_limit"
      params: {...}
      mapping: {...}
```

#### 6.2 API 条件执行
```python
condition:  # 只在满足条件时执行
    if: "price_exists"
    depends_on: ["price"]
```

#### 6.3 字段映射机制 ⭐ 复杂
```python
mapping:
    # 1. 简单映射
    db_field: "api_field"
    
    # 2. 常量值
    db_field: {value: "constant"}
    
    # 3. 转换函数
    db_field: {
        source: "api_field",
        transform: lambda x: x * 100
    }
    
    # 4. 默认值
    db_field: {
        source: "api_field",
        default: 0
    }
```

#### 6.4 数据准备（prepare_data_for_save）⭐ 最常重写
```python
# 子类重写场景：
- 合并多个API数据
- 数据清洗和验证
- 计算衍生字段
- 去重、排序
```

### 7. 错误处理与重试

#### 7.1 事务性原则
```python
# API 调用结果：
None:       真正失败（网络错误、限流报错）→ job失败，下次重试
空DataFrame: 正常（停牌、未交易）→ job成功，不保存数据
```

#### 7.2 Job 失败处理
```python
if failed_apis:
    logger.warning(f"Job执行失败，数据不会保存")
    return None  # job失败，下次会重试

# incremental模式：失败的任务下次自动重试
# overwrite模式：删除表后重建（危险）
```

#### 7.3 数据验证
```python
# DataFrame NaN 处理（智能）
nan_handling:
    auto_convert: true
    allow_null_fields: ["note", "remark"]
    field_defaults:
        price: 0
        volume: 0

# 根据 schema 自动决定：
- float/int → 0
- varchar → ''
- 其他 → None
```

### 8. 特殊处理场景 ⭐ 关键

#### 8.1 股票列表过滤
```python
# 排除规则（在模型内处理）
- 北交所股票（exchange_center = '北交所'）
- ST股票（is_st = 1）
- 退市股票（is_active = 0）

# 方法：load_filtered_stock_list()
```

#### 8.2 复权因子依赖 ⭐ 跨Provider
```python
# AKShare 需要先有 K线数据
ak.inject_dependency(tu)

# 更新顺序：
1. Tushare: 股票列表
2. Tushare: K线数据
3. AKShare: 复权因子（依赖K线）
```

#### 8.3 主键动态生成
```python
# 场景：主键包含日期字段（quarter）
# stock中没有quarter，需要从API返回数据获取

def get_job_primary_keys(stock, db_record, primary_keys):
    # 只返回stock中存在的主键
    # quarter由API数据提供
    return {'id': stock['id']}
```

#### 8.4 宏观数据 vs 股票数据
```python
# 宏观数据：
- 不需要stock_list
- 只有1个job
- 全局更新

# 股票数据：
- 需要stock_list
- N个job（每个股票一个）
- 并行更新
```

---

## 🏗️ 架构组件分析

### 1. 组件层级

```
DataSourceManager（编排器）
    ↓
Tushare / AKShare（Provider）
    ↓
BaseRenewer（更新器基类）
    ↓
具体Renewer（如StockKlineRenewer）
    ↓
TushareStorage（存储层）
```

### 2. 关键组件

#### 2.1 DataSourceManager
```python
职责：
- 管理多个Provider
- 协调更新顺序
- 处理依赖关系（AKShare依赖Tushare）

特点：
- 简单的编排逻辑
- 硬编码的依赖关系
```

#### 2.2 Tushare（Provider）
```python
职责：
- 管理多个Renewer
- 提供API实例
- 管理限流器
- 管理进度跟踪器

特点：
- 包含大量辅助功能
- 线程安全机制
- 认证管理
```

#### 2.3 BaseRenewer（核心）
```python
职责：
- 判断是否需要更新（should_renew）
- 构建任务列表（build_jobs）
- 执行更新（simple/multithread）
- API调用与字段映射
- 数据保存

可重写方法：
- build_jobs()              # 自定义任务构建
- prepare_data_for_save()   # ⭐ 最常重写
- save_data()               # 特殊保存逻辑
- map_api_data()            # API级别映射
- get_job_primary_keys()    # 动态主键
- get_job_log_vars()        # 日志变量
- should_execute_api()      # API条件执行
```

#### 2.4 配置驱动（Config）
```python
每个Renewer有独立配置：
- table_name
- renew_mode
- job_mode
- apis: [...]
- date: {interval, field, api_format, disclosure_delay_months}
- multithread: {workers, log}
- rate_limit: {max_per_minute}
- nan_handling: {...}
```

---

## 🔥 复杂度来源

### 1. 时间处理复杂
- 4种周期类型
- 披露延迟
- 日期格式转换
- 增量计算

### 2. 多线程安全
- 线程局部DB
- 进度计数器加锁
- 限流器线程安全

### 3. 灵活的配置
- 多API组合
- 字段映射
- 条件执行
- 日志模板

### 4. 错误容错
- API失败重试
- 停牌数据处理
- NaN智能转换
- 部分成功处理

### 5. 跨Provider依赖
- AKShare依赖Tushare
- 复权因子依赖K线
- 硬编码的编排逻辑

---

## 🎯 新架构需要保留的核心功能

### 必须保留（不能妥协）

1. ✅ **三种更新模式**（overwrite/incremental/upsert）
2. ✅ **多线程支持**（含线程安全机制）
3. ✅ **限流器**（多层级、buffer机制）
4. ✅ **进度跟踪**（详细日志、可配置）
5. ✅ **增量更新**（智能判断、披露延迟）
6. ✅ **字段映射**（多种方式、转换函数）
7. ✅ **错误重试**（事务性、部分成功）
8. ✅ **配置驱动**（灵活、可扩展）

### 需要改进（可优化）

1. 🔵 **依赖管理**：硬编码 → 配置化/协调层
2. 🔵 **Provider接口**：不统一 → BaseProvider
3. 🔵 **编排逻辑**：分散 → 集中到DataCoordinator
4. 🔵 **测试性**：难以mock → 适配器模式

### 可以简化（低优先级）

1. 🟡 **日志模板**：过于灵活 → 简化为几种标准格式
2. 🟡 **API条件执行**：很少用 → 延后实现
3. 🟡 **多种字段映射**：保留常用的即可

---

## 📊 统计数据

### Tushare Provider
- **Renewers数量**: 10个
  - stock_list
  - stock_kline
  - corporate_finance
  - price_indexes (CPI, PPI, PMI)
  - lpr
  - gdp
  - shibor
  - stock_index_indicator
  - stock_index_indicator_weight
  - industry_capital_flow

### AKShare Provider
- **Renewers数量**: 1个
  - adj_factor（复权因子）

### 代码量估算
- `base_renewer.py`: ~1500行
- 每个具体renewer: ~100-300行
- Tushare主类: ~200行
- AKShare主类: ~300行

---

## 🚀 新架构设计方向

基于以上分析，新架构应该：

### 1. 保持现有功能
- 所有核心功能通过适配器包装
- 0功能损失
- 完全向后兼容

### 2. 改进架构
```
DataSourceManager（统一管理器）
    ↓
ProviderRegistry（动态挂载）
    ↓
DataCoordinator（协调层）
    ↓
TushareAdapter → LegacyTushare（适配器包装）
AKShareAdapter → LegacyAKShare
```

### 3. 统一接口
```python
class BaseProvider:
    def fetch(request: DataRequest) -> DataResponse
    def supports(data_type: str) -> bool
    def renew_all(end_date, stock_list)
```

### 4. 配置驱动的依赖
```yaml
providers:
  akshare:
    dependencies:
      - provider: tushare
        data_type: stock_kline
        required: true
```

---

## ❓ 需要决策的问题

1. **BaseRenewer要不要重构？**
   - 选项A：适配器直接包装，完全保留
   - 选项B：逐步重写，提取核心逻辑
   - **建议**：选项A（Phase 1-3），选项B（Phase 4）

2. **配置格式要不要改？**
   - 当前：Python字典
   - 未来：YAML/JSON
   - **建议**：渐进式，先兼容Python

3. **线程安全要不要统一？**
   - 当前：每个Renewer独立处理
   - 未来：Provider层统一处理
   - **建议**：适配器继承现有机制

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

