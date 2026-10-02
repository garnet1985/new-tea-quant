"""层诊断落盘与口径常量。"""

LAYER_SCHEMA = "1"
PAPER_PATH_DISCLAIMER = (
    "这是每笔机会独立走完目标的纸面结局，含重叠；"
    "不是价格层去重后的交易，也不是组合层资金。"
)

EXIT_LABELS = {
    "stop_loss": "止损",
    "take_profit": "止盈",
    "expired": "过期",
    "protect_loss": "保护止盈",
    "dynamic_loss": "动态止盈",
    "period_end": "期末",
    "simulate_end": "样本边界",
}

PRICE_BOOK_DISCLAIMER = (
    "这是去噪后的等权机会账：近的并成一段、远的各走各的，"
    "已去掉涨跌停 / 停牌买不进。不是组合层资金，也不是枚举全量纸面路径。"
)

PORTFOLIO_DISCLAIMER = (
    "这是资金约束后的账户成交：槽位、现金、单票上限、同股已持仓都会挡住价格账里的机会。"
    "不是价格层等权边，也不是枚举纸面路径。"
)

TOP_N = 5
