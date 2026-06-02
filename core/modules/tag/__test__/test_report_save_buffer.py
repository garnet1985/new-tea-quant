"""TagReportSaveBuffer 单元测试。"""
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
