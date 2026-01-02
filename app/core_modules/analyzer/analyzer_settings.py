

conf = {
    "stock_idx": {
        # 过滤掉退市，有深度退市风险，北交所，以及科创板股票
        "exclude": {
            "start_with": {
                "id": ["688"],
                "name": ["*ST", "ST", "退"],
            },
            "contains": {
                "id": ["BJ"],
            }
        }
    }
}