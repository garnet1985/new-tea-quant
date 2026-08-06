"""BE __performance__ 套件配置（样本规模 / 临时库命名）。

改样本：只改本文件默认值，或 ``db_creation.py --stocks / --start-date / --end-date``。
数据直接注入 DuckDB，无 CSV 中间层。
"""
from __future__ import annotations

# ── 合成数据集默认规模 ──
DATASET_ID = "fake_v1_direct"
DEFAULT_STOCK_COUNT = 1000
DEFAULT_START_DATE = "20230101"
DEFAULT_END_DATE = "20260101"
DEFAULT_SEED = 20260525  # fingerprint only；价格用固定规律，不依赖 RNG
DEFAULT_KLINE_TERM = "daily"

# ── 临时库命名（clean 仅删此前缀）──
DB_NAME_PREFIX = "perf_test_tmp"
