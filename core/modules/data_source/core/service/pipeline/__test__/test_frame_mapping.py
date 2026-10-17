"""列名映射保持为表，缺列按行数补齐。"""
import pandas as pd

from core.modules.data_source.core.service.pipeline.frame_mapping import (
    iter_record_chunks,
    map_columns,
    records_from_frame,
)


def test_map_columns_renames_and_fills_missing_without_dicts():
    raw = pd.DataFrame({"trade_date": ["20200101", "20200102"], "close": [1.5, None]})
    mapped = map_columns(
        raw,
        {"date": "trade_date", "close": "close", "volume": "vol"},
        constants={"id": "000001.SZ", "term": "daily"},
    )
    assert list(mapped.columns) == ["date", "close", "volume", "id", "term"]
    assert len(mapped) == 2
    assert mapped.iloc[0]["id"] == "000001.SZ"
    assert mapped.iloc[0]["volume"] == 0.0
    records = records_from_frame(mapped.iloc[:1])
    assert records[0]["date"] == "20200101"
    assert records[0]["id"] == "000001.SZ"


def test_iter_record_chunks_does_not_return_the_whole_frame_at_once():
    frame = pd.DataFrame({"close": list(range(5))})
    chunks = list(iter_record_chunks(frame, chunk_rows=2))
    assert [len(chunk) for chunk in chunks] == [2, 2, 1]
    assert chunks[0][0]["close"] == 0
    assert chunks[-1][0]["close"] == 4
