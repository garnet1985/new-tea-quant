# analyzer 层诊断测试索引

| 文件 | 覆盖 |
|------|------|
| `test_layer_enumerate.py` | 枚举层事实 / 结论 / 建议；一档全平不可测；分档可测 |
| `test_layer_price.py` | 价格层去噪账边、利润头部、合并偏、涨停跳过 |
| `test_layer_portfolio.py` | 组合层买到/漏掉、槽位顶满、无价格不编差、RSI 分组错位 |
| `test_prepare.py` | as-of 切片 Prepare |
| `test_present.py` | sz `analysis/report.json` 展示 |
| `test_ui_facts.py` | UI facts |
| `test_report_narrative.py` | 切片报告叙事 |
| `test_insights.py` | 切片 insight |
| `test_factor_analysis_pipeline.py` | 因素分析 pipeline |
