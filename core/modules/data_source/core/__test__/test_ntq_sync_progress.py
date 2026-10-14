"""官网同步会在翻页前打出进度，并且只拉这一张表的计划区间。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run


def test_pull_prints_the_page_it_is_waiting_on(capsys):
    from core.modules.data_source.core.progress import SyncProgress
    from core.modules.data_source.core.service import official_sync

    class _Provider:
        def __init__(self):
            self.calls = []

        def sync(self, table, start=None, end=None):
            self.calls.append((table, start, end))
            if len(self.calls) == 1:
                return {"rows": [{"date": "20230101"}], "next_start": "c.2"}
            return {"rows": [{"date": "20230102"}], "next_start": None}

    class _Handler:
        def get_key(self):
            return "cpi"

        def __init__(self):
            self.progress = SyncProgress("cpi")
            self.context = {
                "providers": {"ntq": _Provider()},
                "is_dry_run": False,
            }

    handler = _Handler()
    official_sync._upsert = lambda handler, table, rows: None
    saved = official_sync._pull(handler, "sys_data_cpi", "20230101", "20251231")
    text = capsys.readouterr().out
    assert saved == 2
    assert handler.context["providers"]["ntq"].calls[0] == (
        "sys_data_cpi",
        "20230101",
        "20251231",
    )
    assert "正在读取第 1 页，已写入 0 行" in text
    assert "同步完成 sys_data_cpi（宏观 CPI）写入 2 行" in text
