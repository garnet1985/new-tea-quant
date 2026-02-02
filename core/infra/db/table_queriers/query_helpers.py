"""
QueryHelpers - 查询和格式化辅助工具

提供时序数据查询、DataFrame 支持、Schema 格式化等功能。
"""
from typing import List, Dict, Any, Optional
from loguru import logger


class TimeSeriesHelper:
    """时序数据查询辅助类（通过组合调用，需传入 model 实例）"""

    def __init__(self, model):
        self.model = model

    def load_latest_date(self, date_field: str) -> Optional[str]:
        """
        加载表中最新的日期

        Args:
            date_field: 日期字段名（由调用方传入）
        """
        latest_record = self.model.load_one("1=1", order_by=f"{date_field} DESC")
        return latest_record.get(date_field) if latest_record else None

class DataFrameHelper:
    """DataFrame 支持辅助类（通过组合调用，需传入 model 实例）"""

    def __init__(self, model):
        self.model = model

    def load_many_df(self, condition: str = "1=1", params: tuple = (),
                     limit: int = None, order_by: str = None, offset: int = None):
        """加载多条记录，返回DataFrame"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用load_many_df方法")
            return None
        records = self.model.load_many(condition, params, limit, order_by, offset)
        return pd.DataFrame(records) if records else pd.DataFrame()

    def load_all_df(self, condition: str = "1=1", params: tuple = (), order_by: str = None):
        """加载所有记录，返回DataFrame"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用load_all_df方法")
            return None
        records = self.model.load_all(condition, params, order_by)
        return pd.DataFrame(records) if records else pd.DataFrame()

    def insert_df(self, df) -> int:
        """插入DataFrame数据"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用insert_df方法")
            return 0
        if not isinstance(df, pd.DataFrame):
            logger.error(f"insert_df expects pandas DataFrame, got {type(df)}")
            return 0
        if df.empty:
            logger.debug("DataFrame is empty, skipping insert")
            return 0
        data_list = df.to_dict('records')
        return self.model.insert(data_list)

    def replace_df(self, df, unique_keys: List[str]) -> int:
        """Upsert DataFrame数据（基于唯一键更新或插入）"""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas未安装，无法使用replace_df方法")
            return 0
        if not isinstance(df, pd.DataFrame):
            logger.error(f"replace_df expects pandas DataFrame, got {type(df)}")
            return 0
        if df.empty:
            logger.debug("DataFrame is empty, skipping replace")
            return 0
        data_list = df.to_dict('records')
        return self.model.upsert(data_list, unique_keys)