"""
core.data_class.time_series：时序数据块封装

提供围绕 ColumnarTable 的时序数据视图（如游标推进、按日期窗口访问），
与 Entity（表/字段契约）解耦，便于在不同模块复用。
"""

from core.data_class.time_series.time_series_data import TimeSeriesData

__all__ = ["TimeSeriesData"]

