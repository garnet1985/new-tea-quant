# DateUtils 重新设计文档

> **设计原则**：统一对外接口，降低学习成本，内部模块化实现

---

## 🎯 核心设计理念

### 1. 统一入口原则
- **所有功能都通过 `DateUtils` 类暴露**
- 用户只需要知道 `DateUtils`，不需要了解内部模块
- 内部可以分模块实现，但对外透明

### 2. API 命名规范
- **统一前缀**：同类功能使用统一前缀
  - `normalize_*` - 标准化
  - `to_*` - 格式转换
  - `add_*` / `sub_*` - 加减运算
  - `get_*` - 获取值
  - `is_*` - 判断
  - `diff_*` - 差值计算

- **命名清晰**：方法名自解释，减少文档查阅
  - ✅ `DateUtils.to_period_str(date, "month")` 
  - ❌ `DateUtils.get_current_period(date, "month")` (不清晰)

### 3. 数据格式统一
- **日期**：统一为 `YYYYMMDD` 字符串
- **周期**：统一为字符串
  - 月：`"202401"`
  - 季：`"2024Q1"`
  - 年：`"2024"`

---

## 📦 模块结构（内部实现）

```
core/utils/date/
├── __init__.py              # 只导出 DateUtils
├── _constants.py            # 内部常量（私有）
├── _parser.py              # 内部解析模块（私有）
├── _calculator.py          # 内部计算模块（私有）
├── _period.py              # 内部周期模块（私有）
├── date_utils.py           # 唯一对外接口
├── DESIGN.md               # 本文档
└── __test__/
    └── test_date_utils.py  # 只测试 DateUtils
```

**关键**：所有内部模块用 `_` 前缀，表示私有，用户不需要关心。

---

## 🔧 DateUtils API 设计

### 一、常量定义

```python
class DateUtils:
    # 周期类型常量
    PERIOD_DAY = "day"
    PERIOD_WEEK = "week"
    PERIOD_MONTH = "month"
    PERIOD_QUARTER = "quarter"
    PERIOD_YEAR = "year"
    
    # 格式常量（如果需要）
    FMT_YYYYMMDD = "%Y%m%d"
    FMT_YYYY_MM_DD = "%Y-%m-%d"
```

---

### 二、格式转换（通用 + 特定方向）

#### 通用方法（自动识别输入类型）

```python
@staticmethod
def to_format(input: Any, fmt: str = FMT_YYYYMMDD) -> Optional[str]:
    """
    通用格式化：将任意输入转换为指定格式的字符串
    
    Args:
        input: 可以是 datetime, date, str（自动识别类型）
        fmt: 目标格式（默认 YYYYMMDD）
    
    Returns:
        str: 格式化后的字符串，失败返回 None
    
    Examples:
        to_format(datetime(2024, 1, 15)) -> "20240115"
        to_format(date(2024, 1, 15), FMT_YYYY_MM_DD) -> "2024-01-15"
        to_format("20240115", FMT_YYYY_MM_DD) -> "2024-01-15"
        to_format("2024-01-15") -> "20240115" (自动识别源格式)
    """

@staticmethod
def normalize(input: Any, fmt: str = FMT_YYYYMMDD) -> Optional[str]:
    """
    通用标准化：将任意输入标准化为指定格式（智能识别）
    
    Args:
        input: 可以是 datetime, date, str, YYYYMM, YYYYQ1 等
        fmt: 目标格式（默认 YYYYMMDD）
    
    Returns:
        str: 标准化后的字符串，失败返回 None
    
    Examples:
        normalize("2024-01-15") -> "20240115"
        normalize(datetime(2024, 1, 15)) -> "20240115"
        normalize("202401") -> "20240101" (视为当月第一天)
        normalize("2024Q1") -> "20240101" (视为季度第一天)
        normalize("2024-01-15", FMT_YYYY_MM_DD) -> "2024-01-15" (保持格式)
    """
```

#### 特定方向方法（类型明确）

```python
# ==================== datetime/date → str ====================

@staticmethod
def datetime_to_format(dt: datetime, fmt: str = FMT_YYYYMMDD) -> str:
    """
    明确：datetime → str
    
    Raises:
        ValueError: 如果输入不是 datetime
    """

@staticmethod
def date_to_format(d: date, fmt: str = FMT_YYYYMMDD) -> str:
    """
    明确：date → str
    
    Raises:
        ValueError: 如果输入不是 date
    """

@staticmethod
def normalize_datetime(dt: datetime, fmt: str = FMT_YYYYMMDD) -> str:
    """明确：datetime → str（标准化）"""

@staticmethod
def normalize_date(d: date, fmt: str = FMT_YYYYMMDD) -> str:
    """明确：date → str（标准化）"""

# ==================== str → str ====================

@staticmethod
def str_to_format(date_str: str, to_fmt: str, from_fmt: Optional[str] = None) -> Optional[str]:
    """
    明确：str → str（格式转换）
    
    Args:
        date_str: 源日期字符串
        to_fmt: 目标格式
        from_fmt: 源格式（None 时自动识别）
    
    Returns:
        str: 转换后的字符串，失败返回 None
    """

@staticmethod
def normalize_str(date_str: str, fmt: str = FMT_YYYYMMDD) -> Optional[str]:
    """
    明确：str → str（标准化）
    
    支持自动识别：YYYYMMDD, YYYY-MM-DD, YYYYMM, YYYYQ1 等
    """

# ==================== str → datetime ====================

@staticmethod
def str_to_datetime(date_str: str, fmt: Optional[str] = None) -> datetime:
    """
    明确：str → datetime
    
    Args:
        date_str: 日期字符串
        fmt: 源格式（None 时自动识别）
    
    Returns:
        datetime: 解析后的 datetime 对象
    
    Raises:
        ValueError: 解析失败时抛出
    """
```

**设计理由**：
- **通用方法**：`to_format()` / `normalize()` 自动识别类型，使用灵活
- **特定方法**：`*_to_format()` / `normalize_*()` 类型明确，便于类型检查和 IDE 提示
- **命名规范**：
  - `*_to_format()` - 明确转换方向
  - `normalize_*()` - 明确输入类型
  - `to_format()` / `normalize()` - 通用方法，自动识别

### 转换方向对照表

| 转换方向 | 通用方法 | 特定方法 | 输入类型 | 输出类型 | 错误处理 |
|---------|---------|---------|---------|---------|---------|
| **任意 → str** | `to_format(input, fmt)` | - | Any | str | 返回 None |
| **datetime → str** | `to_format(dt, fmt)` | `datetime_to_format(dt, fmt)` | datetime | str | 通用返回None，特定抛异常 |
| **date → str** | `to_format(d, fmt)` | `date_to_format(d, fmt)` | date | str | 通用返回None，特定抛异常 |
| **str → str** | `to_format(s, fmt)` | `str_to_format(s, to_fmt, from_fmt)` | str | str | 返回 None |
| **str → datetime** | - | `str_to_datetime(s, fmt)` | str | datetime | 抛异常 |
| **任意 → YYYYMMDD** | `normalize(input)` | - | Any | str | 返回 None |
| **datetime → YYYYMMDD** | `normalize(dt)` | `normalize_datetime(dt)` | datetime | str | 通用返回None，特定抛异常 |
| **date → YYYYMMDD** | `normalize(d)` | `normalize_date(d)` | date | str | 通用返回None，特定抛异常 |
| **str → YYYYMMDD** | `normalize(s)` | `normalize_str(s)` | str | str | 返回 None |

### 格式转换使用场景

```python
# 场景 1：处理 API 返回的 datetime 对象
api_response = {"date": datetime(2024, 1, 15)}
date_str = DateUtils.format_datetime(api_response["date"])  # "20240115"

# 场景 2：解析配置文件中的日期字符串
config_date = "2024-01-15"
dt = DateUtils.parse_str(config_date, DateUtils.FMT_YYYY_MM_DD)  # datetime 对象

# 场景 3：数据库存储格式转换
db_date = "20240115"  # 数据库存储格式
display_date = DateUtils.convert_format(db_date, DateUtils.FMT_YYYY_MM_DD)  # "2024-01-15"

# 场景 4：不确定格式的智能识别（最常用）
unknown_format = "2024-01-15"  # 可能是各种格式
normalized = DateUtils.normalize(unknown_format)  # "20240115"（自动识别）
```

---

### 三、日期 ↔ 周期转换

```python
# 日期 → 周期字符串
@staticmethod
def to_period_str(date: str, period_type: str) -> str:
    """
    将日期转换为周期字符串
    
    Args:
        date: YYYYMMDD 格式
        period_type: PERIOD_DAY/MONTH/QUARTER/YEAR
    
    Returns:
        str: 周期字符串
        - DAY -> "20240115"
        - MONTH -> "202401"
        - QUARTER -> "2024Q1"
        - YEAR -> "2024"
    """

# 周期字符串 → 日期
@staticmethod
def from_period_str(period_str: str, period_type: str, is_start: bool = True) -> str:
    """
    将周期字符串转换为日期
    
    Args:
        period_str: 周期字符串
        period_type: PERIOD_DAY/MONTH/QUARTER/YEAR
        is_start: True=起始日，False=结束日
    
    Returns:
        str: YYYYMMDD 格式
    """
```

**设计理由**：
- `to_*` / `from_*` 命名清晰，表示转换方向
- `is_start` 参数统一处理起始/结束日

---

### 四、日期计算

```python
# 基础操作
@staticmethod
def today() -> str:
    """获取今天，返回 YYYYMMDD"""

@staticmethod
def add_days(date: str, days: int) -> str:
    """加 N 天"""

@staticmethod
def sub_days(date: str, days: int) -> str:
    """减 N 天"""

@staticmethod
def diff_days(date1: str, date2: str) -> int:
    """计算天数差（date2 - date1）"""

# 边界获取
@staticmethod
def get_month_start(date: str) -> str:
    """获取月初"""

@staticmethod
def get_month_end(date: str) -> str:
    """获取月末"""

@staticmethod
def get_quarter_start(date: str) -> str:
    """获取季度初"""

@staticmethod
def get_quarter_end(date: str) -> str:
    """获取季度末"""

@staticmethod
def get_week_start(date: str) -> str:
    """获取周一"""

@staticmethod
def get_week_end(date: str) -> str:
    """获取周日"""

# 比较判断
@staticmethod
def is_before(date1: str, date2: str) -> bool:
    """date1 是否在 date2 之前"""

@staticmethod
def is_after(date1: str, date2: str) -> bool:
    """date1 是否在 date2 之后"""

@staticmethod
def is_same(date1: str, date2: str) -> bool:
    """是否同一天"""
```

**设计理由**：
- `today()` 而不是 `get_today_str()`（更简洁）
- `get_*` 前缀统一表示"获取"
- 边界方法名清晰，不需要 `_date` 后缀

---

### 五、周期计算（核心功能）

```python
# 周期加减
@staticmethod
def add_periods(period: str, count: int, period_type: str) -> str:
    """
    周期加法
    
    Examples:
        add_periods("202401", 3, PERIOD_MONTH) -> "202404"
        add_periods("2024Q1", 2, PERIOD_QUARTER) -> "2024Q3"
    """

@staticmethod
def sub_periods(period: str, count: int, period_type: str) -> str:
    """周期减法"""

# 周期比较
@staticmethod
def diff_periods(period1: str, period2: str, period_type: str) -> int:
    """
    计算周期差值
    
    Returns:
        int: period2 - period1 的周期数
    """

@staticmethod
def is_period_before(period1: str, period2: str, period_type: str) -> bool:
    """period1 是否在 period2 之前"""

@staticmethod
def is_period_after(period1: str, period2: str, period_type: str) -> bool:
    """period1 是否在 period2 之后"""

# 周期序列
@staticmethod
def generate_period_range(start: str, end: str, period_type: str) -> List[str]:
    """
    生成周期序列
    
    Examples:
        generate_period_range("202401", "202404", PERIOD_MONTH)
        -> ["202401", "202402", "202403", "202404"]
    """
```

**设计理由**：
- `add_periods` / `sub_periods` 命名清晰
- `diff_periods` 统一差值计算
- `generate_period_range` 提供实用功能

---

### 六、季度专用（高频场景）

```python
@staticmethod
def date_to_quarter(date: str) -> str:
    """YYYYMMDD -> 2024Q1"""

@staticmethod
def quarter_to_date(quarter: str, is_start: bool = True) -> str:
    """
    2024Q1 -> YYYYMMDD
    
    Args:
        is_start: True=季度第一天，False=季度最后一天
    """

@staticmethod
def add_quarters(quarter: str, count: int) -> str:
    """季度加法（便捷方法）"""

@staticmethod
def sub_quarters(quarter: str, count: int) -> str:
    """季度减法（便捷方法）"""

@staticmethod
def diff_quarters(quarter1: str, quarter2: str) -> int:
    """季度差值（便捷方法）"""
```

**设计理由**：
- 季度是高频场景，提供便捷方法
- 避免每次都传 `PERIOD_QUARTER` 参数

---

### 七、周期类型规范化

```python
@staticmethod
def normalize_period_type(period_type: str) -> str:
    """
    规范化周期类型字符串
    
    Examples:
        "daily" -> "day"
        "monthly" -> "month"
        "quarterly" -> "quarter"
    """
```

**设计理由**：
- 统一处理各种输入格式
- 内部使用，但对外暴露（便于配置处理）

---

## 🔄 使用示例

### 示例 1：格式转换（通用方法 vs 特定方法）

```python
from core.utils.date import DateUtils
from datetime import datetime, date

# ==================== 通用方法（自动识别类型）====================

# 通用方法：自动识别输入类型
DateUtils.to_format(datetime(2024, 1, 15))  # "20240115"
DateUtils.to_format(date(2024, 1, 15))  # "20240115"
DateUtils.to_format("20240115")  # "20240115"
DateUtils.to_format("2024-01-15")  # "20240115" (自动识别源格式)

# 通用标准化：智能识别各种格式
DateUtils.normalize("2024-01-15")  # "20240115"
DateUtils.normalize(datetime(2024, 1, 15))  # "20240115"
DateUtils.normalize("202401")  # "20240101" (视为当月第一天)
DateUtils.normalize("2024Q1")  # "20240101" (视为季度第一天)

# ==================== 特定方法（类型明确）====================

# 明确类型：datetime → str
DateUtils.datetime_to_format(datetime(2024, 1, 15))  # "20240115"
DateUtils.normalize_datetime(datetime(2024, 1, 15))  # "20240115"

# 明确类型：date → str
DateUtils.date_to_format(date(2024, 1, 15))  # "20240115"
DateUtils.normalize_date(date(2024, 1, 15))  # "20240115"

# 明确类型：str → str
DateUtils.str_to_format("20240115", DateUtils.FMT_YYYY_MM_DD)  # "2024-01-15"
DateUtils.normalize_str("2024-01-15")  # "20240115"

# 明确类型：str → datetime
dt = DateUtils.str_to_datetime("20240115")  # datetime(2024, 1, 15)
dt2 = DateUtils.str_to_datetime("2024-01-15")  # datetime(2024, 1, 15) (自动识别)
```

**使用建议**：
- **日常使用**：优先用通用方法 `to_format()` / `normalize()`，更灵活
- **类型安全**：需要明确类型时用特定方法，IDE 提示更好
- **批量处理**：用通用方法，自动处理混合类型

### 示例 2：rolling renew 计算

```python
from core.utils.date import DateUtils

# 1. 获取当前周期
today = DateUtils.today()  # "20240115"
current_period = DateUtils.to_period_str(today, DateUtils.PERIOD_MONTH)  # "202401"

# 2. 计算 rolling 窗口起点
start_period = DateUtils.sub_periods(current_period, 12, DateUtils.PERIOD_MONTH)  # "202301"

# 3. 转回日期（如果需要）
start_date = DateUtils.from_period_str(start_period, DateUtils.PERIOD_MONTH)  # "20230101"
```

### 示例 3：handler 日期标准化

```python
from core.utils.date import DateUtils

# API 返回的各种格式
api_dates = ["2024-01-15", "20240115", "202401", "2024Q1"]

for raw_date in api_dates:
    # 统一标准化为日期（智能识别格式）
    date_str = DateUtils.normalize(raw_date)  # 全部转为 YYYYMMDD
    
    # 转为周期字符串
    month_str = DateUtils.to_period_str(date_str, DateUtils.PERIOD_MONTH)  # "202401"
```

### 示例 4：季度处理

```python
from core.utils.date import DateUtils

# 季度操作
current_quarter = "2024Q1"

# 获取上一季度
prev_quarter = DateUtils.sub_quarters(current_quarter, 1)  # "2023Q4"

# 季度转日期
start_date = DateUtils.quarter_to_date(current_quarter, is_start=True)  # "20240101"
end_date = DateUtils.quarter_to_date(current_quarter, is_start=False)  # "20240331"
```

### 示例 5：datetime 对象处理

```python
from core.utils.date import DateUtils
from datetime import datetime, date

# 从 datetime 对象开始
dt = datetime.now()

# 转为字符串
date_str = DateUtils.format_datetime(dt)  # "20240115"

# 进行日期计算
next_month = DateUtils.add_days(date_str, 30)

# 转回 datetime（如果需要）
dt2 = DateUtils.parse_str(next_month)
```

---

## ⚠️ 设计决策与问题

### ✅ 已解决的问题

1. **统一入口**：所有功能通过 `DateUtils`，用户只需学习一个类
2. **命名规范**：统一前缀，方法名自解释
3. **格式统一**：全字符串，无元组混用
4. **错误处理**：
   - `normalize()` 返回 None（宽松）
   - 计算方法抛异常（严格）

### 🤔 需要确认的问题

#### 1. 季度排序问题

**问题**：`"2024Q1"` 格式无法直接字符串排序

**解决方案 A（推荐）**：提供排序辅助
```python
@staticmethod
def get_period_sort_key(period_str: str, period_type: str) -> str:
    """
    获取排序键（用于排序）
    
    Examples:
        get_period_sort_key("2024Q1", PERIOD_QUARTER) -> "20240101"
        get_period_sort_key("202401", PERIOD_MONTH) -> "20240101"
    """
    # 转换为日期作为排序键
    return DateUtils.from_period_str(period_str, period_type)

# 使用
quarters.sort(key=lambda q: DateUtils.get_period_sort_key(q, DateUtils.PERIOD_QUARTER))
```

**解决方案 B**：提供排序方法
```python
@staticmethod
def sort_periods(periods: List[str], period_type: str) -> List[str]:
    """直接排序周期列表"""
```

**建议**：采用方案 A，更灵活

---

#### 2. 周期类型参数传递

**问题**：很多方法需要 `period_type` 参数，是否可以用枚举？

**当前设计**：使用字符串常量
```python
DateUtils.add_periods("202401", 3, DateUtils.PERIOD_MONTH)
```

**替代方案**：使用枚举（但用户要求函数式，枚举可能不符合）
```python
from enum import Enum
class PeriodType(Enum):
    DAY = "day"
    MONTH = "month"
    ...

DateUtils.add_periods("202401", 3, PeriodType.MONTH)
```

**建议**：保持字符串常量，更符合函数式风格

---

#### 3. 错误处理策略

**当前设计**：
- `normalize()` → 返回 None
- `add_days()` → 抛异常
- `to_period_str()` → 抛异常

**问题**：是否统一？

**建议**：
- **解析类**（`normalize`, `to_period_str`）：返回 None（宽松，便于批量处理）
- **计算类**（`add_days`, `add_periods`）：抛异常（严格，避免错误传播）

---

#### 4. 边界情况处理

**需要明确**：
- 无效日期：`"20241301"`（13月）→ 抛异常还是返回 None？
- 无效周期：`"2024Q5"`（第5季度）→ 抛异常
- 跨年计算：`add_periods("202312", 1, PERIOD_MONTH)` → `"202401"`（自动处理）

**建议**：在文档中明确说明，实现时统一处理

---

#### 5. 性能考虑

**潜在问题**：
- 频繁的字符串解析（`"2024Q1"` → `"20240101"` → `"2024Q1"`）
- 周期计算中的格式转换

**优化方案**：
- 内部缓存季度转换结果（季度数量有限）
- 关键路径避免不必要的转换

---

## 📋 API 完整列表

### 常量（5个）
- `PERIOD_DAY`, `PERIOD_WEEK`, `PERIOD_MONTH`, `PERIOD_QUARTER`, `PERIOD_YEAR`
- `FMT_YYYYMMDD`, `FMT_YYYY_MM_DD`, `FMT_YYYYMM`, `FMT_DATETIME`

### 格式转换（9个）

**通用方法（2个）**：
- `to_format(input, fmt=FMT_YYYYMMDD) -> Optional[str]` - 任意 → str（自动识别类型）
- `normalize(input, fmt=FMT_YYYYMMDD) -> Optional[str]` - 任意 → YYYYMMDD（智能标准化）

**特定方向方法（7个）**：
- `datetime_to_format(dt, fmt) -> str` - datetime → str（明确类型）
- `date_to_format(d, fmt) -> str` - date → str（明确类型）
- `str_to_format(date_str, to_fmt, from_fmt=None) -> Optional[str]` - str → str（格式转换）
- `normalize_datetime(dt, fmt) -> str` - datetime → YYYYMMDD（明确类型）
- `normalize_date(d, fmt) -> str` - date → YYYYMMDD（明确类型）
- `normalize_str(date_str, fmt) -> Optional[str]` - str → YYYYMMDD（明确类型）
- `str_to_datetime(date_str, fmt=None) -> datetime` - str → datetime

### 日期 ↔ 周期转换（2个）
- `to_period_str(date, period_type) -> str` - 日期 → 周期字符串
- `from_period_str(period_str, period_type, is_start=True) -> str` - 周期字符串 → 日期

### 日期计算（13个）
- `today() -> str`
- `add_days(date, days) -> str`
- `sub_days(date, days) -> str`
- `diff_days(date1, date2) -> int`
- `get_month_start(date) -> str`
- `get_month_end(date) -> str`
- `get_quarter_start(date) -> str`
- `get_quarter_end(date) -> str`
- `get_week_start(date) -> str`
- `get_week_end(date) -> str`
- `is_before(date1, date2) -> bool`
- `is_after(date1, date2) -> bool`
- `is_same(date1, date2) -> bool`

### 周期计算（6个）
- `add_periods(period, count, period_type) -> str`
- `sub_periods(period, count, period_type) -> str`
- `diff_periods(period1, period2, period_type) -> int`
- `is_period_before(period1, period2, period_type) -> bool`
- `is_period_after(period1, period2, period_type) -> bool`
- `generate_period_range(start, end, period_type) -> List[str]`

### 季度专用（5个）
- `date_to_quarter(date) -> str`
- `quarter_to_date(quarter, is_start=True) -> str`
- `add_quarters(quarter, count) -> str`
- `sub_quarters(quarter, count) -> str`
- `diff_quarters(quarter1, quarter2) -> int`

### 工具方法（2个）
- `normalize_period_type(period_type) -> str`
- `get_period_sort_key(period_str, period_type) -> str`（可选）

**总计**：约 42 个公开方法（9个格式转换 + 33个其他）

---

## 🎯 与旧设计的对比

| 方面 | 旧设计（REFACTOR_PLAN） | 新设计（本文档） |
|------|------------------------|-----------------|
| **对外接口** | 分散在多个模块 | 统一在 DateUtils |
| **学习成本** | 需要了解多个模块 | 只需了解 DateUtils |
| **命名规范** | 不统一（get_today_str vs today） | 统一前缀规范 |
| **季度处理** | 通用方法 + period_type | 专用便捷方法 |
| **错误处理** | 未明确 | 明确策略 |
| **兼容性** | 考虑向后兼容 | 不考虑，全新设计 |

---

## ✅ 验收标准

1. **API 完整性**：覆盖所有现有功能
2. **命名一致性**：同类功能使用统一前缀
3. **文档完整**：每个方法都有清晰的 docstring 和示例
4. **测试覆盖**：核心方法测试覆盖率 > 90%
5. **性能无退化**：关键路径性能不降低
6. **使用简单**：新用户 5 分钟内能上手

---

## 🚀 实施建议

### 阶段 1：实现核心功能
1. 实现 `_constants.py`（常量定义）
2. 实现 `_parser.py`（解析和转换）
3. 实现 `_calculator.py`（日期计算）
4. 实现 `_period.py`（周期计算）

### 阶段 2：组装 DateUtils
1. 在 `date_utils.py` 中实现所有公开方法
2. 内部委托给各模块
3. 编写完整测试

### 阶段 3：迁移业务代码
1. 更新所有调用点
2. 删除旧代码
3. 性能测试和优化

---

*最后更新：2026-02-03*
*设计者：开发团队*
