# DateUtils API 文档

## 概述

`DateUtils` 是统一的日期时间处理工具类，提供所有日期时间相关的转换、计算和格式化功能。

### 设计理念

- **统一入口**：所有功能通过 `DateUtils` 类暴露，降低学习成本
- **类型包容**：方法自动识别输入类型（datetime/date/str），提供便捷的通用方法
- **类型明确**：同时提供类型明确的方法（如 `str_to_format`, `datetime_to_format`）
- **功能完整**：覆盖日期格式化、转换、计算、周期处理等所有场景

### 导入方式

```python
from core.utils.date.date_utils import DateUtils
# 或
from core.utils.date import DateUtils
```

---

## 常量定义

### 格式化字符串常量

```python
DateUtils.FMT_YYYYMMDD      # "%Y%m%d"      -> "20240115"
DateUtils.FMT_YYYY_MM_DD     # "%Y-%m-%d"    -> "2024-01-15"
DateUtils.FMT_YYYYMM         # "%Y%m"        -> "202401"
DateUtils.FMT_YYYYQ          # "%YQ%q"       -> "2024Q1"
DateUtils.FMT_DATETIME        # "%Y-%m-%d %H:%M:%S" -> "2024-01-15 10:30:00"
```

### 周期类型常量

```python
DateUtils.PERIOD_DAY         # "day"
DateUtils.PERIOD_WEEK        # "week"
DateUtils.PERIOD_MONTH       # "month"
DateUtils.PERIOD_QUARTER     # "quarter"
DateUtils.PERIOD_YEAR        # "year"
```

### 默认值

```python
DateUtils.DEFAULT_FORMAT     # FMT_YYYYMMDD
DateUtils.DEFAULT_START_DATE # 系统默认起始日期
```

---

## API 分类

### 1. 格式转换（通用方法）

#### `to_format(input, fmt=None) -> Optional[str]`

通用格式化：将任意输入转换为指定格式的字符串。

**参数：**
- `input`: 可以是 `datetime`, `date`, `str`（自动识别类型）
- `fmt`: 目标格式（默认 `YYYYMMDD`）

**返回：**
- `str`: 格式化后的字符串，失败返回 `None`

**示例：**
```python
DateUtils.to_format(datetime(2024, 1, 15))                    # "20240115"
DateUtils.to_format(date(2024, 1, 15), DateUtils.FMT_YYYY_MM_DD)  # "2024-01-15"
DateUtils.to_format("20240115", DateUtils.FMT_YYYY_MM_DD)     # "2024-01-15"
```

#### `normalize(input, fmt=None) -> Optional[str]`

通用标准化：将任意输入标准化为指定格式（智能识别）。

**参数：**
- `input`: 可以是 `datetime`, `date`, `str`, `YYYYMM`, `YYYYQ1` 等
- `fmt`: 目标格式（默认 `YYYYMMDD`）

**返回：**
- `str`: 标准化后的字符串，失败返回 `None`

**示例：**
```python
DateUtils.normalize("2024-01-15")      # "20240115"
DateUtils.normalize(datetime(2024, 1, 15))  # "20240115"
DateUtils.normalize("202401")          # "20240101" (视为当月第一天)
DateUtils.normalize("2024Q1")          # "20240101" (视为季度第一天)
```

---

### 2. 格式转换（类型明确方法）

#### `datetime_to_format(dt, fmt=None) -> str`

明确：`datetime` → `str`

**参数：**
- `dt`: `datetime` 对象
- `fmt`: 目标格式（默认 `YYYYMMDD`）

**返回：**
- `str`: 格式化后的字符串

**异常：**
- `ValueError`: 如果输入不是 `datetime`

**示例：**
```python
DateUtils.datetime_to_format(datetime(2024, 1, 15))  # "20240115"
DateUtils.datetime_to_format(dt, DateUtils.FMT_YYYY_MM_DD)  # "2024-01-15"
```

#### `date_to_format(d, fmt=None) -> str`

明确：`date` → `str`

**参数：**
- `d`: `date` 对象
- `fmt`: 目标格式（默认 `YYYYMMDD`）

**返回：**
- `str`: 格式化后的字符串

**异常：**
- `ValueError`: 如果输入不是 `date`

**示例：**
```python
DateUtils.date_to_format(date(2024, 1, 15))  # "20240115"
```

#### `str_to_format(date_str, to_fmt, from_fmt=None) -> Optional[str]`

明确：`str` → `str`（格式转换）

**参数：**
- `date_str`: 源日期字符串
- `to_fmt`: 目标格式
- `from_fmt`: 源格式（`None` 时自动识别）

**返回：**
- `str`: 转换后的字符串，失败返回 `None`

**示例：**
```python
DateUtils.str_to_format("20240115", DateUtils.FMT_YYYY_MM_DD)  # "2024-01-15"
DateUtils.str_to_format("2024-01-15", DateUtils.FMT_YYYYMMDD)  # "20240115"
```

#### `normalize_datetime(dt, fmt=None) -> str`

明确：`datetime` → `str`（标准化）

**示例：**
```python
DateUtils.normalize_datetime(datetime(2024, 1, 15))  # "20240115"
```

#### `normalize_date(d, fmt=None) -> str`

明确：`date` → `str`（标准化）

**示例：**
```python
DateUtils.normalize_date(date(2024, 1, 15))  # "20240115"
```

#### `normalize_str(date_str, fmt=None) -> Optional[str]`

明确：`str` → `str`（标准化）

支持自动识别：`YYYYMMDD`, `YYYY-MM-DD`, `YYYYMM`, `YYYYQ1` 等

**示例：**
```python
DateUtils.normalize_str("2024-01-15")  # "20240115"
DateUtils.normalize_str("202401")      # "20240101"
DateUtils.normalize_str("2024Q1")       # "20240101"
```

#### `str_to_datetime(date_str, fmt=None) -> datetime`

明确：`str` → `datetime`

**参数：**
- `date_str`: 日期字符串
- `fmt`: 源格式（`None` 时自动识别）

**返回：**
- `datetime`: 解析后的 `datetime` 对象

**异常：**
- `ValueError`: 解析失败时抛出

**示例：**
```python
DateUtils.str_to_datetime("20240115")  # datetime(2024, 1, 15)
DateUtils.str_to_datetime("2024-01-15")  # datetime(2024, 1, 15)
```

---

### 3. 日期 ↔ 周期转换

#### `to_period_str(date, period_type) -> str`

将日期转换为周期字符串。

**参数：**
- `date`: `YYYYMMDD` 格式
- `period_type`: `PERIOD_DAY`/`MONTH`/`QUARTER`/`YEAR`

**返回：**
- `str`: 周期字符串
  - `DAY` → `"20240115"`
  - `MONTH` → `"202401"`
  - `QUARTER` → `"2024Q1"`
  - `YEAR` → `"2024"`

**示例：**
```python
DateUtils.to_period_str("20240115", DateUtils.PERIOD_DAY)     # "20240115"
DateUtils.to_period_str("20240115", DateUtils.PERIOD_MONTH)   # "202401"
DateUtils.to_period_str("20240115", DateUtils.PERIOD_QUARTER) # "2024Q1"
DateUtils.to_period_str("20240115", DateUtils.PERIOD_YEAR)    # "2024"
```

#### `from_period_str(period_str, period_type, is_start=True) -> str`

将周期字符串转换为日期。

**参数：**
- `period_str`: 周期字符串
- `period_type`: `PERIOD_DAY`/`MONTH`/`QUARTER`/`YEAR`
- `is_start`: `True`=起始日，`False`=结束日

**返回：**
- `str`: `YYYYMMDD` 格式

**示例：**
```python
DateUtils.from_period_str("202401", DateUtils.PERIOD_MONTH, is_start=True)   # "20240101"
DateUtils.from_period_str("202401", DateUtils.PERIOD_MONTH, is_start=False)  # "20240131"
DateUtils.from_period_str("2024Q1", DateUtils.PERIOD_QUARTER, is_start=True)  # "20240101"
DateUtils.from_period_str("2024Q1", DateUtils.PERIOD_QUARTER, is_start=False) # "20240331"
```

---

### 4. 日期计算

#### `today() -> str`

获取今天，返回 `YYYYMMDD`。

**示例：**
```python
DateUtils.today()  # "20240203"
```

#### `add_days(date, days) -> str`

加 N 天。

**参数：**
- `date`: `YYYYMMDD` 格式
- `days`: 天数（可为负数）

**示例：**
```python
DateUtils.add_days("20240115", 5)   # "20240120"
DateUtils.add_days("20240115", -5)  # "20240110"
```

#### `sub_days(date, days) -> str`

减 N 天。

**参数：**
- `date`: `YYYYMMDD` 格式
- `days`: 天数

**示例：**
```python
DateUtils.sub_days("20240115", 5)  # "20240110"
```

#### `diff_days(date1, date2) -> int`

计算天数差（`date2 - date1`）。

**参数：**
- `date1`: `YYYYMMDD` 格式
- `date2`: `YYYYMMDD` 格式

**返回：**
- `int`: 天数差

**示例：**
```python
DateUtils.diff_days("20240101", "20240115")  # 14
DateUtils.diff_days("20240115", "20240101")  # -14
```

#### `get_month_start(date) -> str`

获取月初。

**示例：**
```python
DateUtils.get_month_start("20240115")  # "20240101"
```

#### `get_month_end(date) -> str`

获取月末。

**示例：**
```python
DateUtils.get_month_end("20240115")  # "20240131"
DateUtils.get_month_end("20240215")  # "20240229" (闰年)
```

#### `get_quarter_start(date) -> str`

获取季度初。

**示例：**
```python
DateUtils.get_quarter_start("20240115")  # "20240101"
DateUtils.get_quarter_start("20240515")  # "20240401"
```

#### `get_quarter_end(date) -> str`

获取季度末。

**示例：**
```python
DateUtils.get_quarter_end("20240115")  # "20240331"
DateUtils.get_quarter_end("20240515")  # "20240630"
```

#### `get_week_start(date) -> str`

获取周一。

**示例：**
```python
DateUtils.get_week_start("20240115")  # "20240115" (周一)
DateUtils.get_week_start("20240117")  # "20240115" (周三 -> 周一)
```

#### `get_week_end(date) -> str`

获取周日。

**示例：**
```python
DateUtils.get_week_end("20240115")  # "20240121" (周一 -> 周日)
DateUtils.get_week_end("20240121")  # "20240121" (周日)
```

#### `is_before(date1, date2) -> bool`

`date1` 是否在 `date2` 之前。

**示例：**
```python
DateUtils.is_before("20240101", "20240115")  # True
DateUtils.is_before("20240115", "20240101")  # False
```

#### `is_after(date1, date2) -> bool`

`date1` 是否在 `date2` 之后。

**示例：**
```python
DateUtils.is_after("20240115", "20240101")  # True
DateUtils.is_after("20240101", "20240115")  # False
```

#### `is_same(date1, date2) -> bool`

是否同一天。

**示例：**
```python
DateUtils.is_same("20240115", "20240115")  # True
DateUtils.is_same("20240115", "20240116")  # False
```

#### `is_today(date_str) -> bool`

判断日期是否为今天。

**示例：**
```python
DateUtils.is_today("20240203")  # True (如果今天是 2024-02-03)
DateUtils.is_today("20240115")  # False
```

#### `get_previous_week_end(date) -> str`

获取指定日期所在周的前一周周日。

**示例：**
```python
DateUtils.get_previous_week_end("20240115")  # "20240114" (前一周的周日)
```

#### `get_previous_month_end(date) -> str`

获取指定日期所在月的前一个月最后一天。

**示例：**
```python
DateUtils.get_previous_month_end("20240115")  # "20231231"
DateUtils.get_previous_month_end("20250115")  # "20241231"
```

---

### 5. 周期计算（核心功能）

#### `add_periods(period, count, period_type) -> str`

周期加法。

**参数：**
- `period`: 周期字符串
- `count`: 周期数
- `period_type`: `PERIOD_DAY`/`MONTH`/`QUARTER`/`YEAR`

**示例：**
```python
DateUtils.add_periods("202401", 3, DateUtils.PERIOD_MONTH)    # "202404"
DateUtils.add_periods("2024Q1", 2, DateUtils.PERIOD_QUARTER)  # "2024Q3"
DateUtils.add_periods("2024", 1, DateUtils.PERIOD_YEAR)       # "2025"
```

#### `sub_periods(period, count, period_type) -> str`

周期减法。

**示例：**
```python
DateUtils.sub_periods("202404", 3, DateUtils.PERIOD_MONTH)     # "202401"
DateUtils.sub_periods("2024Q3", 2, DateUtils.PERIOD_QUARTER)  # "2024Q1"
```

#### `diff_periods(period1, period2, period_type) -> int`

计算周期差值。

**参数：**
- `period1`: 周期字符串
- `period2`: 周期字符串
- `period_type`: `PERIOD_DAY`/`MONTH`/`QUARTER`/`YEAR`

**返回：**
- `int`: `period2 - period1` 的周期数

**示例：**
```python
DateUtils.diff_periods("202401", "202404", DateUtils.PERIOD_MONTH)    # 3
DateUtils.diff_periods("2024Q1", "2024Q3", DateUtils.PERIOD_QUARTER)  # 2
```

#### `is_period_before(period1, period2, period_type) -> bool`

`period1` 是否在 `period2` 之前。

**示例：**
```python
DateUtils.is_period_before("202401", "202404", DateUtils.PERIOD_MONTH)  # True
```

#### `is_period_after(period1, period2, period_type) -> bool`

`period1` 是否在 `period2` 之后。

**示例：**
```python
DateUtils.is_period_after("202404", "202401", DateUtils.PERIOD_MONTH)  # True
```

#### `generate_period_range(start, end, period_type) -> List[str]`

生成周期序列。

**参数：**
- `start`: 起始周期字符串
- `end`: 结束周期字符串
- `period_type`: `PERIOD_DAY`/`MONTH`/`QUARTER`/`YEAR`

**返回：**
- `List[str]`: 周期字符串列表

**示例：**
```python
DateUtils.generate_period_range("202401", "202404", DateUtils.PERIOD_MONTH)
# ["202401", "202402", "202403", "202404"]

DateUtils.generate_period_range("2024Q1", "2024Q3", DateUtils.PERIOD_QUARTER)
# ["2024Q1", "2024Q2", "2024Q3"]
```

#### `normalize_period_type(period_type) -> str`

规范化周期类型字符串。

**示例：**
```python
DateUtils.normalize_period_type("daily")     # "day"
DateUtils.normalize_period_type("monthly")   # "month"
DateUtils.normalize_period_type("quarterly") # "quarter"
```

#### `detect_period_type(period_str) -> str`

自动识别周期字符串类型。

**示例：**
```python
DateUtils.detect_period_type("202401")   # "month"
DateUtils.detect_period_type("2024Q1")   # "quarter"
DateUtils.detect_period_type("20240115") # "day"
```

#### `get_period_sort_key(period_str, period_type) -> str`

获取排序键（用于排序）。

将周期字符串转换为日期作为排序键。

**示例：**
```python
DateUtils.get_period_sort_key("202401", DateUtils.PERIOD_MONTH)  # "20240101"
```

#### `normalize_period_value(value, period) -> Optional[str]`

将任意输入标准化为指定周期的字符串表示。

**参数：**
- `value`: 可以是 `datetime`, `date`, `str`（自动识别）
- `period`: `PERIOD_DAY`/`MONTH`/`QUARTER`/`YEAR`

**返回：**
- `str`: 标准化后的周期字符串
  - `PERIOD_DAY` → `"20240115"`
  - `PERIOD_MONTH` → `"202401"`
  - `PERIOD_QUARTER` → `"2024Q1"`
  - `PERIOD_YEAR` → `"2024"`
  失败返回 `None`

**示例：**
```python
DateUtils.normalize_period_value("2024-01-15", DateUtils.PERIOD_MONTH)    # "202401"
DateUtils.normalize_period_value(datetime(2024, 1, 15), DateUtils.PERIOD_QUARTER)  # "2024Q1"
```

---

### 6. 季度专用（便捷方法）

#### `date_to_quarter(date) -> str`

`YYYYMMDD` → `2024Q1`

**示例：**
```python
DateUtils.date_to_quarter("20240115")  # "2024Q1"
DateUtils.date_to_quarter("20240415")  # "2024Q2"
DateUtils.date_to_quarter("20240715")  # "2024Q3"
DateUtils.date_to_quarter("20241015")  # "2024Q4"
```

#### `quarter_to_date(quarter, is_start=True) -> str`

`2024Q1` → `YYYYMMDD`

**参数：**
- `quarter`: 季度字符串（如 `"2024Q1"`）
- `is_start`: `True`=季度第一天，`False`=季度最后一天

**返回：**
- `str`: `YYYYMMDD` 格式

**异常：**
- `ValueError`: 季度格式错误

**示例：**
```python
DateUtils.quarter_to_date("2024Q1", is_start=True)   # "20240101"
DateUtils.quarter_to_date("2024Q1", is_start=False)   # "20240331"
DateUtils.quarter_to_date("2024Q2", is_start=True)   # "20240401"
DateUtils.quarter_to_date("2024Q2", is_start=False)  # "20240630"
```

#### `add_quarters(quarter, count) -> str`

季度加法（便捷方法）。

**示例：**
```python
DateUtils.add_quarters("2024Q1", 2)  # "2024Q3"
DateUtils.add_quarters("2024Q4", 1)  # "2025Q1"
```

#### `sub_quarters(quarter, count) -> str`

季度减法（便捷方法）。

**示例：**
```python
DateUtils.sub_quarters("2024Q3", 2)  # "2024Q1"
DateUtils.sub_quarters("2024Q1", 1)  # "2023Q4"
```

#### `diff_quarters(quarter1, quarter2) -> int`

季度差值（便捷方法）。

**示例：**
```python
DateUtils.diff_quarters("2024Q1", "2024Q3")  # 2
DateUtils.diff_quarters("2023Q4", "2024Q1")  # 1
```

#### `get_current_quarter(date) -> str`

获取指定日期所在的季度（`YYYYQ1` 格式）。

**示例：**
```python
DateUtils.get_current_quarter("20240115")  # "2024Q1"
DateUtils.get_current_quarter("20240515")  # "2024Q2"
```

#### `get_next_quarter(quarter) -> str`

获取下一个季度（便捷方法）。

**示例：**
```python
DateUtils.get_next_quarter("2024Q1")  # "2024Q2"
DateUtils.get_next_quarter("2024Q4")  # "2025Q1"
```

#### `get_quarter_start_date(quarter) -> str`

获取季度起始日期（便捷方法）。

**示例：**
```python
DateUtils.get_quarter_start_date("2024Q1")  # "20240101"
DateUtils.get_quarter_start_date("2024Q2")  # "20240401"
```

---

## 常见使用场景

### 场景 1：日期格式转换

```python
# 从数据库读取的日期字符串转换为标准格式
db_date = "2024-01-15"
standard_date = DateUtils.normalize_str(db_date)  # "20240115"

# datetime 对象转换为字符串
dt = datetime(2024, 1, 15)
date_str = DateUtils.datetime_to_format(dt)  # "20240115"

# 格式转换
formatted = DateUtils.str_to_format("20240115", DateUtils.FMT_YYYY_MM_DD)  # "2024-01-15"
```

### 场景 2：日期计算

```python
# 计算 N 天前/后的日期
today = DateUtils.today()
yesterday = DateUtils.sub_days(today, 1)
next_week = DateUtils.add_days(today, 7)

# 计算日期差
days_diff = DateUtils.diff_days("20240101", "20240115")  # 14

# 获取月初/月末
month_start = DateUtils.get_month_start("20240115")  # "20240101"
month_end = DateUtils.get_month_end("20240115")     # "20240131"
```

### 场景 3：周期处理

```python
# 日期转周期
date = "20240115"
month_period = DateUtils.to_period_str(date, DateUtils.PERIOD_MONTH)    # "202401"
quarter_period = DateUtils.to_period_str(date, DateUtils.PERIOD_QUARTER)  # "2024Q1"

# 周期转日期
start_date = DateUtils.from_period_str("202401", DateUtils.PERIOD_MONTH, is_start=True)   # "20240101"
end_date = DateUtils.from_period_str("202401", DateUtils.PERIOD_MONTH, is_start=False)    # "20240131"

# 周期计算
next_month = DateUtils.add_periods("202401", 1, DateUtils.PERIOD_MONTH)  # "202402"
prev_quarter = DateUtils.sub_periods("2024Q2", 1, DateUtils.PERIOD_QUARTER)  # "2024Q1"

# 生成周期范围
months = DateUtils.generate_period_range("202401", "202404", DateUtils.PERIOD_MONTH)
# ["202401", "202402", "202403", "202404"]
```

### 场景 4：季度处理

```python
# 日期转季度
date = "20240115"
quarter = DateUtils.date_to_quarter(date)  # "2024Q1"

# 季度转日期
quarter_start = DateUtils.quarter_to_date("2024Q1", is_start=True)   # "20240101"
quarter_end = DateUtils.quarter_to_date("2024Q1", is_start=False)    # "20240331"

# 季度计算
next_q = DateUtils.get_next_quarter("2024Q1")  # "2024Q2"
quarters_diff = DateUtils.diff_quarters("2024Q1", "2024Q3")  # 2
```

### 场景 5：数据源 Handler 中的日期处理

```python
# 在 Handler 中标准化日期字段
def on_after_mapping(self, data, context):
    for record in data:
        # 自动识别并标准化日期
        record["date"] = DateUtils.normalize(record["date"])
    return data

# 计算 rolling 日期范围
latest_date = context.get("latest_completed_trading_date")
period_type = DateUtils.PERIOD_QUARTER
end_period = DateUtils.to_period_str(latest_date, period_type)
start_period = DateUtils.sub_periods(end_period, 2, period_type)
start_date = DateUtils.from_period_str(start_period, period_type, is_start=True)
end_date = DateUtils.from_period_str(end_period, period_type, is_start=True)
```

### 场景 6：日期比较和判断

```python
# 日期比较
if DateUtils.is_before("20240101", "20240115"):
    print("date1 在 date2 之前")

if DateUtils.is_today("20240203"):
    print("是今天")

# 周期比较
if DateUtils.is_period_before("202401", "202404", DateUtils.PERIOD_MONTH):
    print("period1 在 period2 之前")
```

---

## 注意事项

1. **默认格式**：所有方法默认使用 `YYYYMMDD` 格式，除非明确指定其他格式。

2. **类型识别**：通用方法（`to_format`, `normalize`）会自动识别输入类型，但类型明确的方法（`str_to_format`, `datetime_to_format`）会进行类型检查。

3. **错误处理**：
   - 通用方法（如 `to_format`, `normalize`）失败时返回 `None`
   - 类型明确的方法（如 `str_to_datetime`）失败时抛出 `ValueError`

4. **周期字符串格式**：
   - 月份：`YYYYMM`（如 `"202401"`）
   - 季度：`YYYYQ[1-4]`（如 `"2024Q1"`）
   - 年份：`YYYY`（如 `"2024"`）
   - 日期：`YYYYMMDD`（如 `"20240115"`）

5. **性能考虑**：所有方法都是静态方法，无需实例化 `DateUtils` 类。

---

## 版本历史

- **v2.0**: 重构为模块化设计，统一对外接口，移除向后兼容方法
- **v1.0**: 初始版本
