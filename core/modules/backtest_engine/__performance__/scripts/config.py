"""BE __performance__ 套件配置（样本规模 / 文件名 / 临时库命名）。

改样本：只改本文件默认值，或 ``data_gen.py --stocks / --start-date / --end-date``。
"""
from __future__ import annotations

# ── 合成数据集默认规模（小流量验收；压测再调大）──
DATASET_ID = "fake_v1_experiment"
DEFAULT_STOCK_COUNT = 5000
DEFAULT_START_DATE = "20230101"
DEFAULT_END_DATE = "20260101"
DEFAULT_SEED = 20260525
DEFAULT_KLINE_TERM = "daily"

# ── fake_data/ 文件名 ──
CSV_STOCK_LIST = "sys_stock_list.csv"
CSV_KLINES = "sys_stock_klines.csv"
CSV_CALENDAR = "sys_trade_calendar.csv"
CSV_ST = "sys_stock_st_periods.csv"
UNIVERSE_TXT = "universe.txt"
DATASET_META = "dataset_meta.json"

# ── 临时库命名（clean 仅删此前缀）──
DB_NAME_PREFIX = "perf_test_tmp"
