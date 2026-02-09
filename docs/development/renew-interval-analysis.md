# Renew Interval 场景分析与性价比评估

## 当前 `on_before_fetch` 中的常见模式

### 1. 间隔更新检查（场景1）
**当前实现**：
- `stock_index_indicator_weight`: 至少30天才更新
- `kline`: 周线至少1周，月线至少1个月

**代码示例**：
```python
# kline handler 的完整逻辑（比我之前描述的复杂得多）

# 1. 查询数据库获取每个股票在 3 个周期的最新日期
stock_latest_dates_by_term = self._query_stock_latest_dates(context, stock_list)
# 返回: {stock_id: {"daily": latest_date, "weekly": latest_date, "monthly": latest_date}}

# 2. 为每个周期计算不同的结束日期
end_dates = {
    "daily": latest_trading_date,  # 日线：使用最新交易日
    "weekly": DateUtils.get_previous_week_end(latest_trading_date),  # 周线：上个完整周
    "monthly": DateUtils.get_previous_month_end(latest_trading_date),  # 月线：上个完整月
}

# 3. 为每个股票和每个周期判断是否需要更新
for stock in stock_list:
    stock_dates = stock_latest_dates_by_term.get(stock_id, {})
    start_dates = {}
    
    for term in ["daily", "weekly", "monthly"]:
        latest_date = stock_dates.get(term)
        end_date = end_dates.get(term)
        
        if latest_date:
            # 已有数据，检查是否需要更新
            if term == "weekly":
                # 周线：只有当时间间隔 >= 1 周时才更新
                time_gap_weeks = DateUtils.get_duration_in_days(latest_date, end_date) // 7
                if time_gap_weeks < 1:
                    continue
            elif term == "monthly":
                # 月线：只有当时间间隔 >= 1 个月时才更新
                latest_dt = DateUtils.parse_yyyymmdd(latest_date)
                end_dt = DateUtils.parse_yyyymmdd(end_date)
                year1, month1 = latest_dt.year, latest_dt.month
                year2, month2 = end_dt.year, end_dt.month
                month_diff = (year2 - year1) * 12 + (month2 - month1)
                if end_dt.day < latest_dt.day:
                    month_diff -= 1
                if month_diff < 1:
                    continue
            
            # 从最新日期 + 1 天开始（增量更新）
            start_date = DateUtils.get_date_after_days(latest_date, 1)
            if start_date > end_date:
                continue
        else:
            # 新股票，使用默认开始日期（全量更新）
            start_date = ConfigManager.get_default_start_date()
        
        start_dates[term] = start_date
    
    # 4. 为每个周期创建 ApiJob
    # 5. 创建 daily_basic ApiJob（需要合并所有周期的日期范围）
    if start_dates:
        min_start_date = min(start_dates.values())
        max_end_date = max(end_dates.get(term, "") for term in start_dates.keys())
        # daily_basic 使用合并后的日期范围
```

**复杂度**：中等（需要查询数据库、计算时间差）

### 2. 固定时间更新（场景2）
**当前实现**：暂无明确实现

**潜在场景**：
- 每周一更新
- 每月1号更新
- 每季度第一个交易日更新

**复杂度**：低（只需判断当前时间）

### 3. 随机抽取/批次更新（场景3）
**当前实现**：
- `corporate_finance`: 滚动批次逻辑，分批更新股票

**代码示例**：
```python
# corporate_finance
if not is_first_run and self.renew_rolling_batch and len(all_stocks) > 0:
    batch_size = max(1, len(all_stocks) // self.renew_rolling_batch)
    # 从 cache 读取批次游标
    cache_key = 'corporate_finance_batch_offset'
    cache_row = data_manager.db_cache.get(cache_key)
    batch_offset = int(cache_row['value']) if cache_row else 0
    # 环形切片
    indices = [(batch_offset + i) % L for i in range(batch_size)]
    effective_stock_list = [all_stocks[i] for i in indices]
    # 更新 offset
    new_offset = (batch_offset + batch_size) % L
```

**复杂度**：高（需要缓存管理、批次计算）

---

## 场景分析与性价比评估

### 场景1：每间隔一段时间才进行renew

**使用频率**：⭐⭐⭐⭐⭐（高频）
- `stock_index_indicator_weight`: 30天间隔
- `kline`: 周线/月线间隔检查

**代码重复度**：⭐⭐⭐⭐（高）
- 多个 handler 都有类似的间隔检查逻辑
- 时间差计算逻辑重复

**实现复杂度**：⭐⭐⭐（中等）
- 需要查询数据库获取最新日期
- 需要计算时间差
- 需要支持不同时间单位（天/周/月）

**性价比**：⭐⭐⭐⭐⭐（**强烈推荐**）

**建议实现**：
```json
{
  "renew_interval": {
    "enabled": true,
    "unit": "day",  // day/week/month
    "value": 30,     // 间隔值
    "field": "date"  // 用于检查的日期字段
  }
}
```

**收益**：
- 消除 2-3 个 handler 中的重复代码
- 统一间隔检查逻辑，减少 bug
- 配置化，易于调整

---

### 场景2：每个固定时间需要renew

**使用频率**：⭐⭐⭐（中频，**新增明确需求**）
- **新增需求**：`corporate_finance` 需要在财报季度月份（1、4、7、10月）进行全量更新
- 其他潜在场景：每周一、每月1号等

**代码重复度**：⭐（低，但新需求明确）

**实现复杂度**：⭐⭐（低-中等）
- 只需判断当前时间是否匹配固定时间点
- 需要支持多种时间模式（每月X号、每年X月等）
- **新增需求**：需要支持月份列表（[1, 4, 7, 10]）

**性价比**：⭐⭐⭐⭐（**推荐实现**，因为有明确需求）

**建议实现**（针对 `corporate_finance` 需求）：
```json
{
  "renew_schedule": {
    "enabled": true,
    "type": "monthly",      // monthly/weekly/daily
    "months": [1, 4, 7, 10],  // 每年这些月份（1=1月，4=4月等）
    "day": 1,              // 每月几号（1-31），可选
    "force_all": true       // 是否强制更新所有实体（忽略批次）
  }
}
```

**收益**：
- 满足 `corporate_finance` 的财报季度更新需求
- 提供通用的固定时间更新能力
- 配置化，易于调整

---

### 场景3：随机抽取N个进行renew

**使用频率**：⭐⭐⭐（中频）
- `corporate_finance`: 滚动批次更新
- 可能用于大数据量的分批处理

**代码重复度**：⭐⭐（中等）
- 目前只有 1 个 handler 使用
- 但逻辑复杂，容易出错

**实现复杂度**：⭐⭐⭐⭐（高）
- 需要缓存管理（批次游标）
- 需要环形切片逻辑
- 需要处理边界情况（批次大小、偏移量）

**性价比**：⭐⭐⭐（**可以考虑**）

**建议实现**：
```json
{
  "renew_batch": {
    "enabled": true,
    "batch_size": 100,        // 每批处理数量
    "cache_key": "handler_name_batch_offset"  // 缓存键名（可选，默认自动生成）
  }
}
```

**收益**：
- 简化 `corporate_finance` 的复杂逻辑
- 提供通用批次处理能力
- 但当前只有 1 个 handler 使用，收益有限

---

## 混合场景分析

### 场景2 + 场景3（固定时间 + 批次）⭐ **新增需求**

**示例**：`corporate_finance` 的需求
- **固定时间**：每年1月、4月、7月、10月初进行全量更新（财报季度）
- **批次更新**：其他时间使用批次更新（游标抽取N个）

**复杂度**：⭐⭐⭐⭐（高）
- 需要判断当前时间是否在固定月份
- 如果在固定月份，跳过批次逻辑，更新所有股票
- 如果不在固定月份，使用批次逻辑

**性价比**：⭐⭐⭐⭐（**推荐实现**）

**实现逻辑**：
```python
# 伪代码
current_month = datetime.now().month
is_quarter_month = current_month in [1, 4, 7, 10]

if is_quarter_month:
    # 财报季度月份：更新所有股票
    effective_stock_list = all_stocks
    # 可能需要特殊处理：更新所有股票的最新季度
else:
    # 其他月份：使用批次更新
    effective_stock_list = batch_select(all_stocks, batch_offset)
```

**配置示例**：
```json
{
  "renew_mode": "incremental",
  "renew_schedule": {
    "enabled": true,
    "type": "monthly",
    "months": [1, 4, 7, 10],
    "day": 1,
    "force_all": true
  },
  "renew_batch": {
    "enabled": true,
    "batch_size": 8
  }
}
```

### 场景1 + 场景3（间隔 + 批次）
**示例**：每30天更新一次，但每次只更新100只股票

**复杂度**：⭐⭐⭐⭐（高）
- 需要同时支持间隔检查和批次处理
- 批次逻辑需要考虑间隔检查的结果

**性价比**：⭐⭐⭐（**中等**）
- 如果场景1和场景3都实现了，组合使用相对简单
- 但需要确保两者兼容

---

## 推荐实现优先级

### 优先级1：场景1（间隔更新）✅
**理由**：
- 使用频率最高（2-3个handler）
- 代码重复度高
- 实现复杂度中等
- 收益明显

**实现建议**：
- 在 `BaseHandler` 或 `RenewManager` 中添加间隔检查逻辑
- 配置化，支持 day/week/month 单位
- 自动查询数据库最新日期并计算时间差

### 优先级2：场景3（批次更新）⚠️
**理由**：
- 当前只有1个handler使用
- 但逻辑复杂，容易出错
- 如果未来有更多handler需要批次处理，收益会增加

**实现建议**：
- 提供通用的批次处理辅助方法
- 支持缓存管理（批次游标）
- 可选功能，不强制使用

### 优先级3：场景2（固定时间）❌
**理由**：
- 当前没有使用场景
- 优先级最低
- 如果未来有明确需求再实现

---

## 实现建议

### 方案A：配置化 + 基类内置（推荐）

**优点**：
- 减少用户代码
- 统一逻辑，减少bug
- 配置清晰

**缺点**：
- 需要扩展配置结构
- 可能不够灵活（特殊场景仍需自定义）

**实现位置**：
- 在 `config.json` 中添加 `renew_interval` 配置
- 在 `BaseHandler` 或 `RenewManager` 中实现通用逻辑
- 在 `on_before_fetch` 之前自动过滤

### 方案B：辅助方法（保守）

**优点**：
- 灵活性高
- 不强制使用
- 实现简单

**缺点**：
- 用户仍需写代码调用
- 不能完全消除重复

**实现位置**：
- 在 `date_range_helper` 或相关服务中添加辅助方法
- 用户可以选择性使用

---

## 最终建议

**推荐实现场景1（间隔更新）**，理由：
1. **高频使用**：2-3个handler都在用
2. **高重复度**：代码逻辑重复
3. **中等复杂度**：实现难度适中
4. **明显收益**：能显著减少用户代码

**实现方式**：配置化 + 基类内置（方案A）

**配置示例**：
```json
{
  "renew_mode": "incremental",
  "renew_interval": {
    "enabled": true,
    "unit": "day",
    "value": 30,
    "field": "date"
  }
}
```

**对于 `corporate_finance` 的具体需求**：
- 支持在配置中声明财报季度月份（1、4、7、10月）
- 在这些月份，跳过批次逻辑，更新所有股票
- 其他月份，使用批次更新逻辑
- 这样可以确保每个财报季度都能及时更新所有股票的财务数据

**配置示例（`corporate_finance`）**：
```json
{
  "renew_mode": "incremental",
  "date_format": "quarter",
  "renew_schedule": {
    "enabled": true,
    "type": "monthly",
    "months": [1, 4, 7, 10],
    "day": 1,
    "force_all": true
  },
  "renew_batch": {
    "enabled": true,
    "batch_size": 8,
    "cache_key": "corporate_finance_batch_offset"
  },
  "rolling_quarters": 3
}
```

**对于场景3（批次更新）**：
- 如果场景1实现后，`corporate_finance` 的代码已经简化很多
- 可以暂时保留自定义实现，或提供辅助方法
- 等有更多handler需要时再考虑内置

**对于场景2（固定时间）**：
- 暂不实现，等有明确需求再说
