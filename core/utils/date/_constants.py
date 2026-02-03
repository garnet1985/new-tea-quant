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
