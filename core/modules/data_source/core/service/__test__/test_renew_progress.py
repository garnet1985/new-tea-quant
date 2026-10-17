"""已经更新到的数据日期：只往前推，每个周期单独保留，会员窗口再截一次。"""

from core.modules.data_source.core.service.renew_progress import (
    _rows_need_backfill,
    apply_member_cap,
    fold_progress,
    keep_forward,
    last_updates_for,
    plain_date,
    remember_settled,
    remember_written_rows,
)


def test_plain_date_keeps_month_day_and_quarter():
    assert plain_date("2025-12-31") == "20251231"
    assert plain_date("202512") == "202512"
    assert plain_date("2025q4") == "2025Q4"
    assert plain_date(None) == ""


def test_keep_forward_does_not_move_backward():
    assert keep_forward("20251231", "20251230") == "20251231"
    assert keep_forward("20251230", "20251231") == "20251231"
    assert keep_forward("", "20251231") == "20251231"
    assert keep_forward("20251231", "") == "20251231"


def test_member_cap_keeps_an_earlier_as_of_and_clips_a_later_day():
    assert apply_member_cap("20260101", "20251231") == "20251231"
    assert apply_member_cap("20240101", "20251231") == "20240101"
    assert apply_member_cap("20261016", None) == "20261016"
    assert apply_member_cap("", "20251231") == "20251231"


class _MarkedProgress:
    def __init__(self):
        self.saved = []

    def load_one(self, where, params=()):
        if params and params[0] == "__renew_progress__":
            return {
                "source": "__renew_progress__",
                "entity_id": "backfill",
                "last_update_date": "done",
            }
        return None

    def load(self, where, params=()):
        source = params[0]
        return [row for row in self.saved if row["source"] == source]

    def save_records(self, records):
        self.saved.extend(records)


class _KlineTable:
    def load_schema(self):
        return {"fields": [{"name": "id"}, {"name": "term"}, {"name": "date"}]}

    def load_latests(self, date_field, groups):
        return [{"id": "000001.SZ", "term": "daily", "date": "20261016"}]

    def load_one(self, where, order_by=None):
        return {"id": "000001.SZ"}


class _KlineConfig:
    def get_data_source_key(self):
        return "stock_klines"

    def get_group_fields(self):
        return ["id", "term"]

    def get_date_field(self):
        return "date"

    def get_table_name(self):
        return "sys_data_stock_klines"

    def get_needs_stock_grouping(self):
        return True

    def is_per_entity(self):
        return True


class _Tables:
    def __init__(self, progress, fact):
        self._tables = {
            "sys_meta_data_renew_progress": progress,
            "sys_data_stock_klines": fact,
        }

    def get_table(self, name):
        return self._tables.get(name)


def test_empty_progress_is_filled_from_the_fact_table():
    progress = _MarkedProgress()
    updates = last_updates_for(_Tables(progress, _KlineTable()), _KlineConfig())
    assert updates == {"000001.SZ::daily": "20261016"}
    assert progress.saved[0]["source"] == "stock_klines"


def test_rows_without_a_term_are_refilled_when_the_source_has_terms():
    assert _rows_need_backfill([], termed=True)
    assert _rows_need_backfill([{"term": ""}], termed=True)
    assert not _rows_need_backfill([{"term": "daily"}], termed=True)
    assert not _rows_need_backfill([{"term": ""}], termed=False)


def test_fold_keeps_each_recorded_term_without_requiring_monthly():
    rows = [
        {"entity_id": "000001.SZ", "term": "daily", "last_update_date": "20251231"},
        {"entity_id": "000001.SZ", "term": "weekly", "last_update_date": "20251226"},
        {"entity_id": "000001.SZ", "term": "monthly", "last_update_date": "20251231"},
        {"entity_id": "000002.SZ", "term": "daily", "last_update_date": "20251231"},
    ]
    assert fold_progress(rows, termed=True) == {
        "000001.SZ::daily": "20251231",
        "000001.SZ::weekly": "20251226",
        "000001.SZ::monthly": "20251231",
        "000002.SZ::daily": "20251231",
    }


def test_fold_without_a_term_uses_the_entity_date():
    rows = [{"entity_id": "_global", "term": "", "last_update_date": "202512"}]
    assert fold_progress(rows, termed=False) == {"_global": "202512"}


class _Progress:
    def __init__(self):
        self.saved = []

    def load(self, condition, params):
        return []

    def save_records(self, records):
        self.saved.extend(records)
        return len(records)


class _Fact:
    def load_schema(self):
        return {"fields": [{"name": "id"}, {"name": "term"}, {"name": "date"}]}


class _Config:
    def get_date_field(self):
        return "date"

    def get_needs_stock_grouping(self):
        return True

    def is_per_entity(self):
        return True

    def get_group_by_key(self):
        return "id"

    def get_table_name(self):
        return "sys_data_stock_klines"


class _Handler:
    def __init__(self, progress, dry_run=False):
        self.progress_model = progress
        self.context = {
            "config": _Config(),
            "data_manager": self,
            "is_dry_run": dry_run,
        }

    def get_key(self):
        return "stock_klines"

    def get_table(self, name):
        if name == "sys_meta_data_renew_progress":
            return self.progress_model
        return _Fact()


def test_written_rows_record_the_latest_date_in_the_batch():
    progress = _Progress()
    handler = _Handler(progress)
    remember_written_rows(handler, [
        {"id": "000001.SZ", "term": "daily", "date": "20251230"},
        {"id": "000001.SZ", "term": "daily", "date": "20251231"},
    ])
    assert progress.saved == [{
        "source": "stock_klines",
        "entity_id": "000001.SZ",
        "term": "daily",
        "last_update_date": "20251231",
    }]


def test_empty_rows_do_not_record_a_date():
    progress = _Progress()
    remember_written_rows(_Handler(progress), [])
    assert progress.saved == []


def test_settled_date_fills_a_term_that_had_no_rows():
    progress = _Progress()
    remember_settled(_Handler(progress), "000001.SZ", "20251231")
    saved = {(row["term"], row["last_update_date"]) for row in progress.saved}
    assert saved == {
        ("daily", "20251231"),
        ("weekly", "20251231"),
        ("monthly", "20251231"),
    }


def test_dry_run_does_not_record_a_settled_date():
    progress = _Progress()
    remember_settled(_Handler(progress, dry_run=True), "000001.SZ", "20251231")
    assert progress.saved == []
