"""
日期时间常量定义模块（内部使用）

所有日期时间相关的常量定义，全局唯一来源。
"""

# 格式化字符串常量
FMT_YYYYMMDD = "%Y%m%d"
FMT_YYYY_MM_DD = "%Y-%m-%d"
FMT_YYYYMM = "%Y%m"
FMT_YYYYQ = "%YQ%q"
FMT_DATETIME = "%Y-%m-%d %H:%M:%S"

# 周期类型常量（供 config / handler 引用）
PERIOD_DAY = "day"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"
PERIOD_QUARTER = "quarter"
PERIOD_YEAR = "year"

# 默认格式
DEFAULT_FORMAT = FMT_YYYYMMDD

# 无界查询上界（YYYYMMDD）；下界见 `core/default_config/data.json` 的 default_start_date（运行时经 ConfigManager）
QUERY_DATE_RANGE_MAX = "20991231"
# 当 data 配置未提供 default_start_date 时的兜底下界
QUERY_DATE_RANGE_FALLBACK_MIN = "19000101"
