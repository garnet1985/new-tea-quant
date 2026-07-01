"""交易日历纯工具。"""

from __future__ import annotations

from bisect import bisect_left
from typing import List, Sequence


class CalendarOpenDateHelper:
    """open_dates 过滤与边界判定（无 DataManager 依赖）。"""

    @staticmethod
    def filter_in_range(
        open_dates: List[str],
        start_date: str,
        end_date: str,
    ) -> List[str]:
        start = str(start_date or "").strip()
        end = str(end_date or "").strip()
        if not start or not end:
            return []
        if start > end:
            start, end = end, start
        return [d for d in open_dates if start <= str(d).strip() <= end]

    @staticmethod
    def is_first_open_of_month(as_of_date: str, open_dates: Sequence[str]) -> bool:
        d = str(as_of_date or "").strip()
        if not d or not open_dates:
            return False
        idx = bisect_left(open_dates, d)
        if idx >= len(open_dates) or open_dates[idx] != d:
            return False
        if idx == 0:
            return True
        return str(open_dates[idx - 1])[:6] != d[:6]

    @staticmethod
    def is_last_open_of_month(as_of_date: str, open_dates: Sequence[str]) -> bool:
        d = str(as_of_date or "").strip()
        if not d or not open_dates:
            return False
        idx = bisect_left(open_dates, d)
        if idx >= len(open_dates) or open_dates[idx] != d:
            return False
        if idx + 1 >= len(open_dates):
            return True
        return str(open_dates[idx + 1])[:6] != d[:6]

    @staticmethod
    def is_first_open_of_year(as_of_date: str, open_dates: Sequence[str]) -> bool:
        d = str(as_of_date or "").strip()
        if not d or not open_dates:
            return False
        idx = bisect_left(open_dates, d)
        if idx >= len(open_dates) or open_dates[idx] != d:
            return False
        if idx == 0:
            return True
        return str(open_dates[idx - 1])[:4] != d[:4]

    @staticmethod
    def is_last_open_of_year(as_of_date: str, open_dates: Sequence[str]) -> bool:
        d = str(as_of_date or "").strip()
        if not d or not open_dates:
            return False
        idx = bisect_left(open_dates, d)
        if idx >= len(open_dates) or open_dates[idx] != d:
            return False
        if idx + 1 >= len(open_dates):
            return True
        return str(open_dates[idx + 1])[:4] != d[:4]


__all__ = ["CalendarOpenDateHelper"]
