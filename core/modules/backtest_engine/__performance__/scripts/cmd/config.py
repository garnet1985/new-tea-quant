"""BE __performance__ 套件配置（样本规模 / 临时库命名）。

改样本：只改本文件默认值，或 ``db_creation.py --stocks / --start-date / --end-date``。
``DEFAULT_STOCK_COUNT`` = 入库最大股票数；``bpe``/``bps`` 自动按
``SCALE_FRACTIONS`` 跑多档子集（同库、截取前 N 只，不反复 seed）。
数据直接注入临时库，无 CSV 中间层。
"""
from __future__ import annotations

# ── 合成数据集默认规模 ──
DATASET_ID = "fake_v1_direct"
DEFAULT_STOCK_COUNT = 2000  # 最大 entity 数（入库 + 满档跑测）
DEFAULT_START_DATE = "20230101"
DEFAULT_END_DATE = "20260101"
DEFAULT_SEED = 20260525  # fingerprint only；价格用固定规律，不依赖 RNG
DEFAULT_KLINE_TERM = "daily"

# 跑测自动分档：相对最大股票数的比例（从小到大；同一次命令跑完）
# 例：1000 → N250 / N500 / N1000
SCALE_FRACTIONS = (0.25, 0.5, 1.0)

# ── 临时库命名（clean 仅删此前缀）──
DB_NAME_PREFIX = "perf_test_tmp"
