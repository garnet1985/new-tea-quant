"""
确保 DataKey 与 default_map 完整对齐，避免新增 key 漏注册。
"""
from __future__ import annotations

import sys
import unittest

# 无 pandas 时注入占位，已安装则用真实包。
try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    _pd = types.ModuleType("pandas")
    _pd.DataFrame = object  # type: ignore[attr-defined]
    sys.modules["pandas"] = _pd

from core.modules.data_contract.contract_const import DataKey
from core.modules.data_contract.mapping import default_map


class TestMappingCompleteness(unittest.TestCase):
    def test_default_map_covers_all_data_keys(self) -> None:
        missing = [k.value for k in DataKey if k not in default_map]
        self.assertEqual(missing, [], f"default_map 缺少 DataKey 注册: {missing}")

