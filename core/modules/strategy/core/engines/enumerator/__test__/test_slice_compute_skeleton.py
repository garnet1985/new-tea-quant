#!/usr/bin/env python3
"""slice_based calendar 工具单元测试。"""

from __future__ import annotations

import unittest

from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper


class TestSliceCalendarHelpers(unittest.TestCase):
    def test_open_date_year_boundaries(self) -> None:
        open_dates = ["20231229", "20240102", "20241231"]
        self.assertTrue(CalendarOpenDateHelper.is_first_open_of_year("20240102", open_dates))
        self.assertTrue(CalendarOpenDateHelper.is_last_open_of_year("20241231", open_dates))
        self.assertFalse(CalendarOpenDateHelper.is_first_open_of_year("20240103", open_dates))


if __name__ == "__main__":
    unittest.main()
