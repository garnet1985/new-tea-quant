"""
演示数据导出配置。

``python devcli.py ex`` 默认行为（本文件为唯一配置源）：
- 股票池：``TARGET_STOCK_COUNT > 0`` 时分层抽样（默认 **300**）；``<= 0`` 为全市场
- 时序日期窗：**20250101** ~ **20260101**（``DEFAULT_START_DATE`` / ``DEFAULT_END_DATE``）
- 季度窗：**2025Q1** ~ **2025Q4**（财报等季度表）
- 输出（进 Git / 安装）：``setup/init_data/data_demo.zip``（固定名，每次覆盖）
- 可选 ``--tagged``：额外写一份带版本号的 ``data_v*`` 副本（不提交 Git）
- 仅导出行情/财报/宏观等**数据表**；不含 cache、meta、tag、工作台快照等运行时生成表
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

# 仓库根（config 位于 devtools/demo_exporter/）
REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_JSON = REPO_ROOT / "core" / "system.json"
INIT_DATA_DIR = REPO_ROOT / "setup" / "init_data"
# 可选：``--export-dir devtools/export_output`` 时写入
ALT_EXPORT_DIR = REPO_ROOT / "devtools" / "export_output"

# 进仓库 / 安装向导使用的固定 zip 名（勿改，避免 Git 里堆积 data_v0.3.x_*.zip）
GIT_DATA_ZIP_NAME = "data_demo.zip"
GIT_DATA_META_NAME = "data_demo.meta.json"

# --tagged 时额外副本：data_v{core_version}_{stock_count}_{from}_{to}.zip
PACKAGE_NAME_PREFIX = "data"

# 时间窗（YYYYMMDD / 季度与日期窗对齐）
DEFAULT_START_DATE = "20250101"
DEFAULT_END_DATE = "20260101"
DEFAULT_START_QUARTER = "2025Q1"
DEFAULT_END_QUARTER = "2025Q4"

# 分层抽样目标股票数；<= 0 表示不抽样，导出全市场股票
TARGET_STOCK_COUNT = 500
SAMPLE_RANDOM_SEED = 20250525

# 每个非空分层至少保留 1 只（在目标总数允许时）
MIN_PER_STRATUM = 1

DateFilter = Optional[Tuple[str, str]]  # (column, kind)  kind: yyyymmdd | quarter

# 运行时 / 框架生成表：永不打入演示数据包（即使用 --tables 指定也会跳过）
EXCLUDED_GENERATED_TABLES = frozenset(
    {
        "sys_cache",
        "sys_meta_info",
        "sys_tag_value",
        "sys_tag_scenario",
        "sys_tag_definition",
        "sys_strategy_workbench_snapshot",
    }
)


@dataclass(frozen=True)
class TableExportSpec:
    """单表导出规则。"""

    date_filter: DateFilter = None
    stock_column: Optional[str] = None  # 按股票池过滤的列名；None 表示不按股票过滤


# 逻辑表 -> 导出规格（顺序即导出顺序；仅数据表）
EXPORT_TABLES: Dict[str, TableExportSpec] = {
    # --- 股票池主表（仅导出抽样结果）---
    "sys_stock_list": TableExportSpec(stock_column="id"),
    # --- 时序 / 事件（股票 + 日期）---
    "sys_stock_klines": TableExportSpec(("date", "yyyymmdd"), stock_column="id"),
    "sys_stock_indicators": TableExportSpec(("date", "yyyymmdd"), stock_column="id"),
    "sys_stock_moneyflow": TableExportSpec(("date", "yyyymmdd"), stock_column="id"),
    "sys_adj_factor_events": TableExportSpec(("event_date", "yyyymmdd"), stock_column="id"),
    "sys_corporate_finance": TableExportSpec(("quarter", "quarter"), stock_column="id"),
    "sys_stock_st_periods": TableExportSpec(("start_date", "yyyymmdd"), stock_column="stock_id"),
    # --- 指数（全市场代表，不按股票池过滤）---
    "sys_index_klines": TableExportSpec(("date", "yyyymmdd")),
    "sys_index_weight": TableExportSpec(("date", "yyyymmdd")),
    "sys_index_list": TableExportSpec(),
    # --- 宏观（仅日期窗）---
    "sys_gdp": TableExportSpec(("quarter", "quarter")),
    "sys_cpi": TableExportSpec(("date", "yyyymmdd")),
    "sys_ppi": TableExportSpec(("date", "yyyymmdd")),
    "sys_pmi": TableExportSpec(("date", "yyyymmdd")),
    "sys_money_supply": TableExportSpec(("date", "yyyymmdd")),
    "sys_shibor": TableExportSpec(("date", "yyyymmdd")),
    "sys_lpr": TableExportSpec(("date", "yyyymmdd")),
    "sys_trade_calendar": TableExportSpec(("cal_date", "yyyymmdd")),
    # --- 维表：字典全量；映射表仅抽样股票 ---
    "sys_industries": TableExportSpec(),
    "sys_boards": TableExportSpec(),
    "sys_markets": TableExportSpec(),
    "sys_areas": TableExportSpec(),
    "sys_stock_industry_map": TableExportSpec(stock_column="stock_id"),
    "sys_stock_board_map": TableExportSpec(stock_column="stock_id"),
    "sys_stock_market_map": TableExportSpec(stock_column="stock_id"),
    "sys_stock_area_map": TableExportSpec(stock_column="stock_id"),
}

LIST_STATUS_LABELS = {
    "L": "上市",
    "D": "退市",
    "P": "暂停上市",
}
