

conf = {
    "stock_idx": {
        # 过滤掉退市，有深度退市风险，北交所，以及科创板股票
        "avoid_name_starts_with": ["*ST", "退"],
        "avoid_code_starts_with": ["688"],
        "avoid_exchange_center": ["BJ"]
    }
}