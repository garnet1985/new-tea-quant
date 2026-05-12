"""
通用工具模块

提供配置文件的加载、合并等工具方法。
pandas 仅在操作 DataFrame/Series 的方法内按需 import，避免轻量路径（如 DateUtils）顶层依赖 pandas。
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Set, Tuple


class Utils:
    @staticmethod
    def is_datetime(obj: Any) -> bool:
        return isinstance(obj, datetime.datetime)

    @staticmethod
    def is_date_string(obj: Any) -> bool:
        return Utils.is_string(obj) and obj.isdigit()

    @staticmethod
    def is_dict(obj: Any) -> bool:
        return isinstance(obj, dict)

    @staticmethod
    def is_list(obj: Any) -> bool:
        return isinstance(obj, list)

    @staticmethod
    def is_set(obj: Any) -> bool:
        return isinstance(obj, set)

    @staticmethod
    def is_string(obj: Any) -> bool:
        return isinstance(obj, str)

    @staticmethod
    def is_int(obj: Any) -> bool:
        return isinstance(obj, int)

    @staticmethod
    def is_float(obj: Any) -> bool:
        return isinstance(obj, float)

    @staticmethod
    def is_bool(obj: Any) -> bool:
        return isinstance(obj, bool)

    @staticmethod
    def is_df(obj: Any) -> bool:
        import pandas as pd

        return isinstance(obj, pd.DataFrame)

    @staticmethod
    def is_df_column(obj: Any) -> bool:
        import pandas as pd

        return isinstance(obj, pd.Series)

    @staticmethod
    def deep_merge(defaults: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典

        Args:
            defaults: 默认字典
            custom: 自定义字典
        Returns:
            合并后的字典
        """
        merged = {**defaults, **custom}
        for key, value in custom.items():
            if key in defaults:
                if Utils.is_dict(defaults[key]) and Utils.is_dict(value):
                    merged[key] = Utils.deep_merge(defaults[key], value)
                else:
                    merged[key] = value
        return merged

    @staticmethod
    def df_to_dict(df: Any) -> Dict[str, Any]:
        import pandas as pd

        if not isinstance(df, pd.DataFrame):
            raise TypeError("df_to_dict expects a pandas.DataFrame")
        return df.to_dict(orient="records")

    @staticmethod
    def dict_to_df(data: Dict[str, Any]) -> Any:
        import pandas as pd

        return pd.DataFrame(data)

    @staticmethod
    def df_to_header_and_lines(df: Any) -> Tuple[List[str], List[List[Any]]]:
        import pandas as pd

        if not isinstance(df, pd.DataFrame):
            raise TypeError("df_to_header_and_lines expects a pandas.DataFrame")
        return df.columns.tolist(), df.values.tolist()

    @staticmethod
    def header_and_lines_to_df(header: List[str], lines: List[List[Any]]) -> Any:
        import pandas as pd

        return pd.DataFrame(lines, columns=header)
