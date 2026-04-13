"""
确保 DataKey 与 default_map 完整对齐，避免新增 key 漏注册。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 与 smoke test 保持一致：在 import core.* 前注入 pandas 占位，避免环境差异导致导入失败。
if "pandas" not in sys.modules:
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

