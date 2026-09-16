import unittest

from core.tables.stock.stock_st_periods.st_period_rules import (
    ST_LEVEL_STAR_ST,
    ST_LEVEL_ST,
    bare_stock_name,
    classify_st_level,
    consolidate_st_periods,
    is_active_on,
    overlapping_window_sql,
    period_overlaps_window,
    records_to_st_periods,
)


class TestStPeriodRules(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify_st_level("*ST天山"), ST_LEVEL_STAR_ST)
        self.assertEqual(classify_st_level("ST联创"), ST_LEVEL_ST)
        self.assertEqual(classify_st_level("SST自仪"), "SST")
        self.assertIsNone(classify_st_level("贵州茅台"))

    def test_bare_stock_name_strips_status_markers(self):
        self.assertEqual(bare_stock_name("*ST吉药(退)"), "吉药")
        self.assertEqual(bare_stock_name("ST联创"), "联创")
        self.assertEqual(bare_stock_name("S*ST生化"), "生化")
        self.assertEqual(bare_stock_name("SST自仪"), "自仪")
        self.assertEqual(bare_stock_name("工智退"), "工智")
        self.assertEqual(bare_stock_name("*ST工智退"), "工智")
        self.assertEqual(bare_stock_name("退市华业"), "华业")
        self.assertEqual(bare_stock_name("贵州茅台"), "贵州茅台")
        self.assertEqual(bare_stock_name(""), "")

    def test_is_active_on_inclusive_end(self):
        period = {
            "st_level": ST_LEVEL_ST,
            "start_date": "20010508",
            "end_date": "20061008",
        }
        self.assertTrue(is_active_on(period, "20010508"))
        self.assertTrue(is_active_on(period, "20061008"))
        self.assertFalse(is_active_on(period, "20061009"))
        self.assertFalse(is_active_on(period, "20010507"))

    def test_period_overlaps_window_keeps_open_interval_started_before(self):
        open_star = {
            "st_level": ST_LEVEL_STAR_ST,
            "start_date": "20240430",
            "end_date": None,
        }
        self.assertTrue(period_overlaps_window(open_star, "20250101", "20260101"))
        self.assertTrue(period_overlaps_window(open_star, "20230101", "20260101"))
        ended_before = {
            "st_level": ST_LEVEL_ST,
            "start_date": "20200101",
            "end_date": "20241231",
        }
        self.assertFalse(period_overlaps_window(ended_before, "20250101", "20260101"))
        starts_after = {
            "st_level": ST_LEVEL_ST,
            "start_date": "20260201",
            "end_date": None,
        }
        self.assertFalse(period_overlaps_window(starts_after, "20250101", "20260101"))

    def test_overlapping_window_sql_bind_order(self):
        sql = overlapping_window_sql()
        self.assertIn("start_date <= %s", sql)
        self.assertIn("end_date >= %s", sql)
        self.assertIn("end_date IS NULL", sql)

    def test_records_to_st_periods(self):
        rows = records_to_st_periods(
            [
                {
                    "name": "ST测试",
                    "start_date": "20200102",
                    "end_date": "20200601",
                    "change_reason": "ST",
                },
                {"name": "正常股份", "start_date": "20200602", "end_date": None},
            ],
            stock_id="000001.SZ",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["st_level"], ST_LEVEL_ST)
        self.assertEqual(rows[0]["stock_id"], "000001.SZ")

    def test_consolidate_closes_open_end_before_next_start(self):
        periods = consolidate_st_periods(
            [
                {
                    "stock_id": "000806.SZ",
                    "st_level": ST_LEVEL_ST,
                    "start_date": "20190329",
                    "end_date": None,
                    "source": "namechange",
                },
                {
                    "stock_id": "000806.SZ",
                    "st_level": ST_LEVEL_STAR_ST,
                    "start_date": "20200601",
                    "end_date": None,
                    "source": "namechange",
                },
            ]
        )
        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0]["end_date"], "20200531")


if __name__ == "__main__":
    unittest.main()
