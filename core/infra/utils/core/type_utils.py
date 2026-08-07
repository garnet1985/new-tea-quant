"""
类型判断、字典深合并/差异、DataFrame 薄封装。

公开入口：``Utils.types``。
pandas 仅在 DataFrame/Series 方法内按需 import，避免轻量路径顶层依赖 pandas。
"""
from __future__ import annotations

import copy
import datetime
from typing import Any, Dict, List, Set, Tuple


class TypeUtils:
    @staticmethod
    def is_datetime(obj: Any) -> bool:
        return isinstance(obj, datetime.datetime)

    @staticmethod
    def is_date_string(obj: Any) -> bool:
        return TypeUtils.is_string(obj) and obj.isdigit()

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
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典（override 覆盖 base 同键叶子值）。

        Args:
            base: 基准字典
            override: 覆盖字典
        Returns:
            合并后的字典（新字典，不修改原始字典）
        """
        merged = copy.deepcopy(base)

        for key, value in override.items():
            if key in merged:
                if TypeUtils.is_dict(merged[key]) and TypeUtils.is_dict(value):
                    merged[key] = TypeUtils.deep_merge(merged[key], value)
                else:
                    merged[key] = copy.deepcopy(value)
            else:
                # 新增字段
                merged[key] = copy.deepcopy(value)

        return merged

    @staticmethod
    def deep_diff(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度对比两个字典的差异（返回 override 相对于 base 的差异）。

        Args:
            base: 基准字典
            override: 对比字典

        Returns:
            差异字典（只包含 override 相对于 base 的差异）
        """
        diff: Dict[str, Any] = {}

        for key in override:
            value_base = base.get(key)
            value_override = override[key]

            # override 有但 base 没有的（新增）
            if key not in base:
                diff[key] = copy.deepcopy(value_override)
                continue

            # 值不同
            if isinstance(value_base, dict) and isinstance(value_override, dict):
                # 递归对比嵌套字典
                nested_diff = TypeUtils.deep_diff(value_base, value_override)
                if nested_diff:
                    diff[key] = nested_diff
            elif value_base != value_override:
                # 值不同（非嵌套）
                diff[key] = copy.deepcopy(value_override)

        return diff

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


__all__ = ["TypeUtils"]
