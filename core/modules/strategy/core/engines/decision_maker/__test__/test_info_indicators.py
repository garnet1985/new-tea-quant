"""决策者 info 指标列：多输出（vortex）须进表，不能被声明名 vortex14 滤掉。"""

from __future__ import annotations

from core.modules.strategy.core.engines.decision_maker.info import load_info_table


def _bars(n: int = 80):
    rows = []
    for i in range(n):
        month = 1 if i < 31 else 2
        day = i + 1 if i < 31 else i - 30
        rows.append(
            {
                "date": f"2023{month:02d}{day:02d}",
                "open": 10.0 + i * 0.01,
                "high": 10.5 + i * 0.01,
                "low": 9.5 + i * 0.01,
                "close": 10.2 + i * 0.01,
                "volume": 1000 + i,
                # 行情元数据：不得被当成指标画上主图
                "amount": 1_000_000 + i * 1000,
                "pre_close": 10.0 + i * 0.01,
            }
        )
    return rows


def test_load_info_table_keeps_vortex_vtx_columns():
    bars = _bars()

    def load(_eid, _cutoff, limit):
        return list(bars[-int(limit) :])

    cols, rows = load_info_table(
        entity_id="002351.SZ",
        as_of="20230220",
        n=40,
        keep=None,
        indicators_cfg={"cmf": [{"length": 20}], "vortex": [{"length": 14}]},
        load_bars=load,
    )
    assert "cmf20" in cols
    assert "vtxp_14" in cols
    assert "vtxm_14" in cols
    assert "amount" not in cols
    assert "pre_close" not in cols
    assert any(row.get("vtxp_14") is not None for row in rows)
    assert any(row.get("vtxm_14") is not None for row in rows)
