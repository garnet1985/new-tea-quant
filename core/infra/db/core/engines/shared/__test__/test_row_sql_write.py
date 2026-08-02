"""row_sql 写入口规范化。"""
from decimal import Decimal

import numpy as np

from core.infra.db.core.engines.shared import row_sql


def test_normalize_write_rows():
    rows = row_sql.normalize_write_rows(
        [{"n": np.int64(3), "f": Decimal("1.5")}]
    )
    assert rows[0]["n"] == 3
    assert rows[0]["f"] == 1.5
    assert isinstance(rows[0]["f"], float)
