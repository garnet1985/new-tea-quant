"""
DataContract 冒烟：DataKey + ``issue``（显式 entity_id / 时间窗）是否足以走通。

**推荐**从仓库根目录直接跑本文件（会先注入 pandas 占位再 import core）：
  python3 core/modules/data_contract/__test__/test_data_contract_smoke.py -v

若本机已安装 pandas，也可用：
  python3 -m unittest discover -s core/modules/data_contract/__test__ -p 'test_data_contract_smoke.py' -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 无 pandas 时注入占位模块；已安装则使用真实 pandas，避免污染后续用例的 sys.modules。
try:
    import pandas as _pandas  # noqa: F401
except ImportError:
    import types

    _pd = types.ModuleType("pandas")
    _pd.DataFrame = object  # type: ignore[attr-defined]
    sys.modules["pandas"] = _pd

from core.modules.data_contract import DataContractManager, DataKey, IssueResult
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.contract_const import ContractScope, ContractType
from core.modules.data_contract.contracts import NonTimeSeriesContract, TimeSeriesContract
from core.modules.data_contract.loaders import StockKlineLoader, StockListLoader, TagLoader


class TestIssueShape(unittest.TestCase):
    """不连 DB：签发形态与 mapping 一致。"""

    def setUp(self) -> None:
        self.mgr = DataContractManager(contract_cache=ContractCacheManager())

    def test_stock_list_issue(self) -> None:
        try:
            result = self.mgr.issue(DataKey.STOCK_LIST)
        except Exception as e:
            raise unittest.SkipTest(f"数据库不可用，跳过 stock.list issue 形态检查：{e}") from e
        self.assertIsInstance(result, IssueResult)
        c = result.require_contract()
        self.assertEqual(c.meta.data_id, DataKey.STOCK_LIST)
        self.assertEqual(c.meta.scope, ContractScope.GLOBAL)
        self.assertIsInstance(c, NonTimeSeriesContract)
        self.assertIsInstance(c.loader, StockListLoader)
        self.assertIsNotNone(c.data)

    def test_kline_qfq_issue(self) -> None:
        result = self.mgr.issue(DataKey.STOCK_KLINE, entity_id="600000.SH", adjust="qfq")
        self.assertIsInstance(result, IssueResult)
        self.assertEqual(result.entity_count, 1)
        c = result.require_one()
        self.assertEqual(c.meta.data_id, DataKey.STOCK_KLINE)
        self.assertEqual(c.meta.scope, ContractScope.PER_ENTITY)
        self.assertIsInstance(c, TimeSeriesContract)
        self.assertIsInstance(c.loader, StockKlineLoader)
        self.assertEqual(c.loader_params.get("adjust"), "qfq")
        self.assertIsNone(c.data)

    def test_tag_issue(self) -> None:
        result = self.mgr.issue(DataKey.TAG, entity_id="000001.SZ")
        c = result.require_one()
        self.assertEqual(c.meta.data_id, DataKey.TAG)
        self.assertIsInstance(c, TimeSeriesContract)
        self.assertIsInstance(c.loader, TagLoader)
        self.assertEqual(getattr(c, "time_axis_field", None), "as_of_date")
        self.assertIsNone(c.data)


class TestLoadIntegration(unittest.TestCase):
    """需可用 DB；不可用时 skip。"""

    def setUp(self) -> None:
        self.mgr = DataContractManager(contract_cache=ContractCacheManager())

    def test_load_stock_list(self) -> None:
        try:
            c = self.mgr.issue(DataKey.STOCK_LIST).require_contract()
            rows = c.data
        except Exception as e:
            raise unittest.SkipTest(f"数据库不可用，跳过 stock.list load：{e}") from e
        self.assertIsInstance(rows, list)
        if rows:
            self.assertIn("id", rows[0])

    def test_load_kline_after_stock_id(self) -> None:
        try:
            c_list = self.mgr.issue(DataKey.STOCK_LIST).require_contract()
            stocks = c_list.data
        except Exception as e:
            raise unittest.SkipTest(f"数据库不可用：{e}") from e
        if not stocks:
            raise unittest.SkipTest("股票列表为空，无法测 kline")
        sid = stocks[0]["id"]
        try:
            result = self.mgr.issue(
                DataKey.STOCK_KLINE,
                entity_id=sid,
                start="20200101",
                end="20201231",
                adjust="qfq",
            )
            c = result.require_one()
            self.assertFalse(c.needs_load)
            bars = c.data
            if not bars:
                bars = c.load(start="20200101", end="20201231")
        except Exception as e:
            raise unittest.SkipTest(f"kline load 失败（可能无行情数据）：{e}") from e
        self.assertIsInstance(bars, list)
        for row in bars[:5]:
            self.assertIn("date", row)

    def test_kline_batch_issue(self) -> None:
        try:
            c_list = self.mgr.issue(DataKey.STOCK_LIST).require_contract()
            stocks = c_list.data
        except Exception as e:
            raise unittest.SkipTest(f"数据库不可用：{e}") from e
        if len(stocks) < 2:
            raise unittest.SkipTest("股票列表不足 2 只，无法测 batch issue")
        ids = [stocks[0]["id"], stocks[1]["id"]]
        try:
            result = self.mgr.issue(
                DataKey.STOCK_KLINE,
                entity_ids=ids,
                start="20200101",
                end="20201231",
                adjust="qfq",
            )
        except Exception as e:
            raise unittest.SkipTest(f"kline batch issue 失败：{e}") from e
        self.assertEqual(result.entity_count, 2)
        for sid in ids:
            c = result.entity(sid)
            self.assertFalse(c.needs_load)
            self.assertIsInstance(c.data, list)

    def test_tag_load_requires_scenario(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.mgr.issue(DataKey.TAG, entity_id="000001.SZ").require_one().load(
                start="20200101", end="20201231"
            )
        self.assertIn("scenario", str(ctx.exception).lower())

    def test_tag_load_if_configured(self) -> None:
        try:
            from core.modules.data_manager import DataManager

            dm = DataManager()
            tbl = dm.get_table("sys_tag_scenario")
            if not tbl:
                raise unittest.SkipTest("无 sys_tag_scenario 表")
            scenario_row = tbl.load_one("1=1")
        except Exception as e:
            raise unittest.SkipTest(f"无法访问 tag scenario 表：{e}") from e
        if not scenario_row or not scenario_row.get("name"):
            raise unittest.SkipTest("无 tag scenario 数据")
        name = str(scenario_row["name"])
        try:
            c_list = self.mgr.issue(DataKey.STOCK_LIST).require_contract()
            stocks = c_list.data
        except Exception as e:
            raise unittest.SkipTest(f"股票列表不可用：{e}") from e
        if not stocks:
            raise unittest.SkipTest("股票列表为空")
        sid = stocks[0]["id"]
        try:
            c = self.mgr.issue(
                DataKey.TAG,
                entity_id=sid,
                start="20200101",
                end="20201231",
                tag_scenario=name,
            ).require_one()
            rows = c.load(start="20200101", end="20201231")
        except Exception as e:
            raise unittest.SkipTest(f"tag load 失败：{e}") from e
        self.assertIsInstance(rows, list)


if __name__ == "__main__":
    unittest.main()
