# DateUtils 重构设计文档

> **重构目标**：统一日期时间处理逻辑，职责清晰，易于维护和扩展

---

## 📋 重构原则

1. **统一字符串表示**：所有周期值用字符串表示，便于存储和传递
2. **职责单一**：每个模块只做一件事
3. **函数式风格**：保持当前的函数式 API，简单直观
4. **向后兼容**：保留 `DateUtils` 作为统一入口
5. **适度类型检查**：关键接口加类型标注，内部保持灵活

---

## 🎯 数据格式规范

### 周期字符串格式（统一标准）

| 周期类型 | 格式 | 示例 | 说明 |
|---------|------|------|------|
| **日** | `YYYYMMDD` | `20240115` | 8位数字 |
| **周** | `YYYYMMDD` | `20240115` | 使用周一日期表示 |
| **月** | `YYYYMM` | `202401` | 6位数字 |
| **季** | `YYYYQ[1-4]` | `2024Q1` | 年份+Q+季度号 |
| **年** | `YYYY` | `2024` | 4位数字 |

### 配置中的周期 Key（PeriodType）

```python
PERIOD_DAY = "day"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"
PERIOD_QUARTER = "quarter"
PERIOD_YEAR = "year"
```

---

## 📦 模块划分

```
core/utils/date/
├── __init__.py              # 导出统一接口
├── constants.py             # 所有常量定义
├── period.py               # 周期处理（核心）
├── calculator.py           # 日期计算
├── parser.py               # 格式解析和标准化
├── date_utils.py           # 统一入口（向后兼容）
├── REFACTOR_PLAN.md        # 本文档
└── __test__/
    ├── test_period.py
    ├── test_calculator.py
    └── test_parser.py
```

---

## 🔧 模块职责

### 1. `constants.py` - 常量定义中心

**职责**：所有日期时间相关的常量定义，全局唯一来源

**内容**：
- 格式化字符串常量（`FMT_YYYYMMDD`, `FMT_YYYY_MM_DD` 等）
- 周期类型常量（`PERIOD_DAY`, `PERIOD_MONTH` 等）
- 默认值常量

**原则**：
- 所有魔法字符串都定义为常量
- 其他模块/文件只能引用，不能重新定义

---

### 2. `parser.py` - 格式解析与转换

**职责**：处理各种输入格式的解析和标准化

**核心功能**：

#### 解析与标准化
- `normalize(date_input: Any) -> Optional[str]`
  - 统一入口：将任意输入转为 YYYYMMDD
  - 支持：YYYYMMDD, YYYY-MM-DD, datetime, date, YYYYMM, 2024Q1 等

#### 周期转换
- `to_period_str(date: str, period_type: str) -> str`
  - 将 YYYYMMDD 转换为周期字符串
  - 示例：`("20240115", "month") -> "202401"`
  
- `from_period_str(period_str: str, period_type: str) -> str`
  - 将周期字符串转换为 YYYYMMDD（默认取起始日）
  - 示例：`("202401", "month") -> "20240101"`

#### 季度专用
- `date_to_quarter(date: str) -> str`
  - YYYYMMDD -> 2024Q1
  
- `quarter_to_date(quarter: str, is_start: bool = True) -> str`
  - 2024Q1 -> YYYYMMDD

#### 解析为对象
- `parse(date_str: str, fmt: Optional[str] = None) -> datetime`
  - 解析为 datetime 对象
  
- `format(dt: datetime, fmt: str = FMT_YYYYMMDD) -> str`
  - datetime 格式化为字符串

**原则**：
- 只负责格式转换，不做计算
- 输入宽松（支持多种格式），输出严格（统一格式）
- 解析失败返回 None，不抛异常

---

### 3. `calculator.py` - 日期计算

**职责**：日期的加减、比较、边界计算

**核心功能**：

#### 基础操作
- `today() -> str` - 获取今天（YYYYMMDD）
- `add_days(date: str, days: int) -> str` - 加 N 天
- `sub_days(date: str, days: int) -> str` - 减 N 天
- `diff_days(date1: str, date2: str) -> int` - 天数差

#### 边界获取
- `get_month_start(date: str) -> str` - 月初
- `get_month_end(date: str) -> str` - 月末
- `get_quarter_start(date: str) -> str` - 季度初
- `get_quarter_end(date: str) -> str` - 季度末
- `get_week_start(date: str) -> str` - 周一
- `get_week_end(date: str) -> str` - 周日

#### 比较判断
- `is_before(date1: str, date2: str) -> bool`
- `is_after(date1: str, date2: str) -> bool`
- `is_same(date1: str, date2: str) -> bool`

**原则**：
- 只处理日期（YYYYMMDD），不涉及周期
- 所有输入输出都是字符串
- 计算失败时抛出明确的异常

---

### 4. `period.py` - 周期处理（核心）

**职责**：周期的加减、比较、转换（最复杂的逻辑）

**核心功能**：

#### 周期加减
- `add_periods(period: str, count: int, period_type: str) -> str`
  - 周期加法
  - 示例：`("202401", 3, "month") -> "202404"`
  - 示例：`("2024Q1", 2, "quarter") -> "2024Q3"`

- `sub_periods(period: str, count: int, period_type: str) -> str`
  - 周期减法
  - 示例：`("202404", 3, "month") -> "202401"`

#### 周期比较
- `diff_periods(period1: str, period2: str, period_type: str) -> int`
  - 计算周期差值
  - 示例：`("202401", "202404", "month") -> 3`

- `is_period_before(period1: str, period2: str, period_type: str) -> bool`
- `is_period_after(period1: str, period2: str, period_type: str) -> bool`

#### 周期识别与规范化
- `normalize_period_type(period_type: str) -> str`
  - 将各种写法统一为标准 period_type
  - 示例：`"daily" -> "day"`, `"monthly" -> "month"`

- `detect_period_type(period_str: str) -> str`
  - 自动识别周期字符串类型
  - 示例：`"202401" -> "month"`, `"2024Q1" -> "quarter"`

#### 周期序列生成
- `generate_period_range(start: str, end: str, period_type: str) -> List[str]`
  - 生成周期序列
  - 示例：`("202401", "202404", "month") -> ["202401", "202402", "202403", "202404"]`

**原则**：
- 所有周期值用字符串表示
- 支持不同粒度的周期互转
- 计算要考虑跨年、跨季等边界情况

---

### 5. `date_utils.py` - 统一入口

**职责**：向后兼容 + 提供便捷方法

**结构**：
```python
class DateUtils:
    """统一入口类，委托给各专门模块"""
    
    # ==================== 常量 ====================
    # 从 constants 导入
    PERIOD_DAY = constants.PERIOD_DAY
    PERIOD_MONTH = constants.PERIOD_MONTH
    ...
    
    # ==================== 解析与标准化 ====================
    # 委托给 parser
    @staticmethod
    def normalize(date_input):
        return parser.normalize(date_input)
    
    # ==================== 日期计算 ====================
    # 委托给 calculator
    @staticmethod
    def add_days(date, days):
        return calculator.add_days(date, days)
    
    # ==================== 周期处理 ====================
    # 委托给 period
    @staticmethod
    def add_periods(period, count, period_type):
        return period.add_periods(period, count, period_type)
    
    # ==================== 向后兼容方法 ====================
    # 保留旧方法名，内部委托
    @staticmethod
    def get_current_period(date, date_format):
        """旧方法：返回元组，保持兼容"""
        ...
```

**原则**：
- 提供所有常用方法的快捷访问
- 旧方法保留，逐步标记为 deprecated
- 新代码应直接使用各专门模块

---

## 🔄 关键数据流

### 场景 1：周期计算（rolling renew）

```python
# 当前做法（有元组转换）
end_value = DateUtils.get_current_period("20240115", "month")  # (2024, 1)
start_value = DateUtils.subtract_periods(end_value, 12, "month")  # (2023, 1)
start_date = DateUtils.format_period(start_value, "month")  # "202301"

# 重构后（全字符串）
from core.utils.date import parser, period

end_period = parser.to_period_str("20240115", "month")  # "202401"
start_period = period.sub_periods(end_period, 12, "month")  # "202301"
# 如果需要转回日期
start_date = parser.from_period_str(start_period, "month")  # "20230101"
```

### 场景 2：日期标准化（handler）

```python
# 当前做法
normalized = DateUtils.normalize_period_value("2024-01-15", "month")  # "202401"

# 重构后
from core.utils.date import parser

date_str = parser.normalize("2024-01-15")  # "20240115"
period_str = parser.to_period_str(date_str, "month")  # "202401"
```

### 场景 3：季度处理（财务数据）

```python
# 当前做法
quarter = DateUtils.date_to_quarter("20240115")  # "2024Q1"
start_date = DateUtils.quarter_to_date("2024Q1", is_start=True)  # "20240101"

# 重构后（保持不变）
from core.utils.date import parser

quarter = parser.date_to_quarter("20240115")  # "2024Q1"
start_date = parser.quarter_to_date("2024Q1", is_start=True)  # "20240101"
```

---

## 🚀 迁移策略

### 阶段 1：创建新模块（不影响现有代码）
- [ ] 创建 `constants.py`，迁移所有常量
- [ ] 创建 `parser.py`，实现解析和转换
- [ ] 创建 `calculator.py`，实现日期计算
- [ ] 创建 `period.py`，实现周期处理
- [ ] 编写完整单元测试

### 阶段 2：重构 `date_utils.py`
- [ ] 将现有方法委托给新模块
- [ ] 标记即将废弃的方法（`@deprecated`）
- [ ] 更新文档和类型标注

### 阶段 3：逐步迁移业务代码
- [ ] 优先级 1：renew 相关（rolling/incremental）
- [ ] 优先级 2：handler 相关（normalize）
- [ ] 优先级 3：其他业务代码
- [ ] 每个模块迁移后跑一遍测试

### 阶段 4：清理
- [ ] 删除未使用的旧方法
- [ ] 删除注释掉的代码
- [ ] 统一代码风格

---

## ⚠️ 注意事项

### 元组 vs 字符串问题

**当前问题**：
```python
# 现在有些方法返回元组
get_current_period("20240115", "month")  # -> (2024, 1)
format_period((2024, 1), "month")  # -> "202401"
```

**迁移方案**：
1. 新 API 全部用字符串
2. 旧 API 保留元组形式（向后兼容）
3. 提供转换辅助函数：
   - `period.to_tuple(period_str, period_type) -> Tuple[int, ...]`
   - `period.from_tuple(period_tuple, period_type) -> str`

### 季度格式问题

**当前**：混用 `2024Q1` 和 `202401Q1`

**统一为**：`2024Q1`（简洁格式）

**排序问题解决**：
```python
# 方案 1：排序时转换
quarters.sort(key=lambda q: parser.quarter_to_date(q))

# 方案 2：提供排序辅助
from core.utils.date import period
quarters.sort(key=period.get_period_sort_key)
```

### 类型标注策略

**关键接口**：严格类型标注
```python
def add_periods(period: str, count: int, period_type: str) -> str:
    """严格标注：外部调用的核心方法"""
```

**内部辅助**：适度标注
```python
def _parse_quarter(quarter_str):
    """内部方法，保持灵活"""
```

---

## 📚 API 速查表

### 常用操作快速参考

| 需求 | 新 API | 旧 API（兼容） |
|------|--------|---------------|
| 标准化日期 | `parser.normalize(date)` | `DateUtils.normalize_date(date)` |
| 日期加减 | `calculator.add_days(date, n)` | `DateUtils.add_days(date, n)` |
| 月初月末 | `calculator.get_month_start(date)` | `DateUtils.get_month_start_date(date)` |
| 周期加减 | `period.add_periods(p, n, type)` | `DateUtils.add_one_period(...)` |
| 周期差值 | `period.diff_periods(p1, p2, type)` | `DateUtils.calculate_period_diff(...)` |
| 转周期串 | `parser.to_period_str(date, type)` | - |
| 季度转换 | `parser.date_to_quarter(date)` | `DateUtils.date_to_quarter(date)` |

---

## 📝 示例代码

### 示例 1：rolling renew 计算

```python
from core.utils.date import parser, period, calculator

# 1. 获取当前周期
today = calculator.today()
current_period = parser.to_period_str(today, "month")  # "202401"

# 2. 计算 rolling 窗口起点
start_period = period.sub_periods(current_period, 12, "month")  # "202301"

# 3. 生成周期序列（可选）
period_range = period.generate_period_range(start_period, current_period, "month")
# ["202301", "202302", ..., "202401"]

# 4. 转回日期（如果需要）
start_date = parser.from_period_str(start_period, "month")  # "20230101"
```

### 示例 2：handler 日期标准化

```python
from core.utils.date import parser

# API 返回的各种格式
api_dates = ["2024-01-15", "20240115", "202401", "2024Q1"]

# 统一标准化
for raw_date in api_dates:
    normalized = parser.normalize(raw_date)  # 全部转为 YYYYMMDD
    
    # 根据需要转为周期字符串
    month_str = parser.to_period_str(normalized, "month")  # "202401"
```

### 示例 3：季度数据处理

```python
from core.utils.date import parser, period

# 季度字符串操作
current_quarter = "2024Q1"

# 获取上一季度
prev_quarter = period.sub_periods(current_quarter, 1, "quarter")  # "2023Q4"

# 季度转日期（用于查询数据库）
start_date = parser.quarter_to_date(current_quarter, is_start=True)  # "20240101"
end_date = parser.quarter_to_date(current_quarter, is_start=False)  # "20240331"
```

---

## ✅ 验收标准

重构完成后应满足：

1. **功能完整**：所有现有功能都有对应实现
2. **测试覆盖**：核心方法测试覆盖率 > 90%
3. **文档齐全**：每个公开方法都有清晰的 docstring
4. **性能无退化**：关键路径性能不降低
5. **向后兼容**：现有代码无需修改即可运行
6. **代码简洁**：新代码行数 < 当前的 70%

---

## 📅 时间规划

- **阶段 1**：2-3 天（新模块实现 + 测试）
- **阶段 2**：1 天（重构 date_utils.py）
- **阶段 3**：3-5 天（业务代码迁移）
- **阶段 4**：1 天（清理和优化）

**总计**：约 1-2 周

---

## 🎓 设计思想

### 为什么要分模块？

1. **职责单一**：每个文件只关注一个领域，易于理解和维护
2. **依赖清晰**：`period` 依赖 `parser`，`date_utils` 依赖所有，层次分明
3. **测试友好**：每个模块独立测试，问题定位快
4. **扩展方便**：未来新增功能只需修改对应模块

### 为什么统一用字符串？

1. **直观**：`"202401"` 比 `(2024, 1)` 更直观
2. **存储友好**：数据库、配置文件都是字符串
3. **类型安全**：避免 `(2024, 1)` 被误解为坐标等其他含义
4. **格式统一**：所有周期值用同一套规则处理

### 为什么保留函数式风格？

1. **简单**：无需实例化对象，直接调用
2. **无状态**：纯函数，易于测试和并发
3. **符合习惯**：Python 日期处理通常用函数式
4. **轻量级**：不引入额外的类层次结构

---

## 🔗 相关文档

- [TermType 枚举定义](../../global_enums/enums.py)
- [DateUtils 单元测试](../../utils/__test__/test_date_utils.py)
- [数据源 renew 机制](../../modules/data_source/README.md)

---

*最后更新：2026-02-03*
*维护者：开发团队*
