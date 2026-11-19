"""
演示数据导出配置。

``python devcli.py ex`` 需指定预设（本文件为日期/抽样默认值的唯一配置源）：

- ``--demo``：分层抽样 ``TARGET_STOCK_COUNT``（默认 **300**）+ 默认日期窗
- ``--member``：全市场 + 默认日期窗（会员安装包）
- ``--full``：全市场 + 忽略日期窗（全历史）
- 无参数：只显示帮助，不导出

日期窗默认：**20230101** ~ **20251231**；季度窗：**2023Q1** ~ **2025Q4**。
输出：``userspace/.ntq/packages/{demo|member|full}/``（与安装下载共用；按类型分目录）。
安装下载源：官网 ``ntq_data/assets/install/``（导出后手动复制上去）。
可选 ``--tagged``：额外写一份带版本号的 ``data_v*`` 副本（不提交 Git）。
仅导出行情/财报/宏观等**数据表**；不含 cache、meta、tag、工作台快照等运行时生成表。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# 仓库根（config 位于 core/infra/setup/core/steps/import_data/export/）
from core.infra.setup.core.shared.install_runtime import REPO_ROOT

SYSTEM_JSON = REPO_ROOT / "core" / "system.json"

# --tagged 时额外副本：data_v{core_version}_{stock_count}_{from}_{to}.zip
PACKAGE_NAME_PREFIX = "data"

# 时间窗（YYYYMMDD / 季度与日期窗对齐）
DEFAULT_START_DATE = "20230101"
DEFAULT_END_DATE = "20251231"
DEFAULT_START_QUARTER = "2023Q1"
DEFAULT_END_QUARTER = "2025Q4"

# 分层抽样目标股票数；<= 0 表示不抽样，导出全市场股票
TARGET_STOCK_COUNT = 300
SAMPLE_RANDOM_SEED = 20250525

# 每个非空分层至少保留 1 只（在目标总数允许时）
MIN_PER_STRATUM = 1

DateFilter = Optional[Tuple[str, str]]
# (column, kind)  kind:
#   yyyymmdd          — 点时序：column BETWEEN 窗起、窗尾
#   yyyymmdd_overlap  — 区间时序：与窗相交（column=起点，结束列固定 end_date）
#   quarter           — 季度 BETWEEN

# 运行时 / 框架生成表：永不打入演示数据包（即使用 --tables 指定也会跳过）
EXCLUDED_GENERATED_TABLES = frozenset(
    {
        "sys_cache_kv",
        "sys_meta_info",
        "sys_data_tag_value",
        "sys_data_tag_scenario",
        "sys_data_tag_definition",
        "sys_meta_tag_calc_progress",
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
    "sys_data_stock_list": TableExportSpec(stock_column="id"),
    # --- 时序 / 事件（股票 + 日期）---
    "sys_data_stock_klines": TableExportSpec(("date", "yyyymmdd"), stock_column="id"),
    "sys_data_stock_indicators": TableExportSpec(("date", "yyyymmdd"), stock_column="id"),
    "sys_data_stock_moneyflow": TableExportSpec(("date", "yyyymmdd"), stock_column="id"),
    "sys_data_adj_factor_events": TableExportSpec(("event_date", "yyyymmdd"), stock_column="id"),
    "sys_data_corporate_finance": TableExportSpec(("quarter", "quarter"), stock_column="id"),
    # ST 时段按与窗相交导出：窗口前已戴帽、窗内仍有效的行要留下（保留真实 start_date）
    "sys_data_stock_st_periods": TableExportSpec(
        ("start_date", "yyyymmdd_overlap"), stock_column="stock_id"
    ),
    # --- 指数（全市场代表，不按股票池过滤）---
    "sys_data_index_klines": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_index_weight": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_index_list": TableExportSpec(),
    # --- 宏观（仅日期窗）---
    "sys_data_gdp": TableExportSpec(("quarter", "quarter")),
    "sys_data_cpi": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_ppi": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_pmi": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_money_supply": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_shibor": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_lpr": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_trade_calendar": TableExportSpec(("cal_date", "yyyymmdd")),
    # --- 维表：字典全量；映射表仅抽样股票 ---
    "sys_data_sw_industry": TableExportSpec(),
    "sys_data_sw_industry_kline": TableExportSpec(("date", "yyyymmdd")),
    "sys_data_boards": TableExportSpec(),
    "sys_data_markets": TableExportSpec(),
    "sys_data_areas": TableExportSpec(),
    "sys_map_sw_stock_industry": TableExportSpec(stock_column="stock_id"),
    "sys_map_stock_board": TableExportSpec(stock_column="stock_id"),
    "sys_map_stock_market": TableExportSpec(stock_column="stock_id"),
    "sys_map_stock_area": TableExportSpec(stock_column="stock_id"),
}

LIST_STATUS_LABELS = {
    "L": "上市",
    "D": "退市",
    "P": "暂停上市",
}
