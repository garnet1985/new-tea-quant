"""TagReportSaveBuffer 单元测试。"""
from pathlib import Path

from core.modules.tag.components.report_save_buffer import TagReportSaveBuffer


def _row(n: int) -> dict:
    return {"entity_id": f"e{n}", "value": str(n)}


def test_flush_when_batch_size_reached():
    saved: list[list] = []

    buf = TagReportSaveBuffer(
        lambda rows: saved.append(list(rows)) or len(rows),
        batch_size=3,
    )
    assert buf.extend([_row(1), _row(2)]) == 0.0
    assert len(saved) == 0
    assert buf.extend([_row(3)]) > 0.0
    assert len(saved) == 1
    assert len(saved[0]) == 3
    assert buf.saved_row_count == 3


def test_final_flush():
    saved: list[list] = []

    buf = TagReportSaveBuffer(
        lambda rows: saved.append(list(rows)) or len(rows),
        batch_size=10,
    )
    buf.extend([_row(1), _row(2)])
    buf.flush()
    assert len(saved) == 1
    assert len(saved[0]) == 2
    assert buf.flush_count == 1


def test_multiple_flushes():
    saved: list[list] = []

    buf = TagReportSaveBuffer(
        lambda rows: saved.append(list(rows)) or len(rows),
        batch_size=2,
    )
    buf.extend([_row(1), _row(2), _row(3), _row(4)])
    assert len(saved) == 2
    assert [len(c) for c in saved] == [2, 2]
    assert buf.flush() == 0.0
    assert len(saved) == 2


def test_accumulate_only_defers_flush_until_explicit_flush():
    saved: list[list] = []

    buf = TagReportSaveBuffer(
        lambda rows: saved.append(list(rows)) or len(rows),
        batch_size=3,
        accumulate_only=True,
    )
    buf.extend([_row(i) for i in range(10)])
    assert len(saved) == 0
    assert buf.pending_row_count == 10
    buf._save_fn = lambda rows: saved.append(list(rows)) or len(rows)
    buf.flush()
    assert len(saved) == 1
    assert len(saved[0]) == 10


def test_spill_to_disk_then_persist(tmp_path: Path):
    saved: list[list] = []

    buf = TagReportSaveBuffer(
        lambda rows: 0,
        batch_size=100,
        accumulate_only=True,
        spill_row_threshold=3,
        spill_dir=tmp_path,
    )
    buf.extend([_row(i) for i in range(5)])
    assert buf.pending_row_count == 0
    assert buf.spill_count == 1
    assert list(tmp_path.glob("*.parquet"))
    assert saved == []
    n = buf.persist_accumulated(
        lambda rows: saved.append(list(rows)) or len(rows),
        batch_size=2,
    )
    assert n >= 0
    assert sum(len(c) for c in saved) == 5
    assert buf.saved_row_count == 5


def test_extend_in_chunks_matches_extend():
    saved: list[list] = []

    buf = TagReportSaveBuffer(
        lambda rows: saved.append(list(rows)) or len(rows),
        batch_size=3,
    )
    rows = [_row(i) for i in range(7)]
    buf.extend_in_chunks(rows)
    buf.flush()
    flat = [r["entity_id"] for chunk in saved for r in chunk]
    assert flat == [f"e{i}" for i in range(7)]
