# price_factor 测试索引

| 文件 | 覆盖 |
|------|------|
| `test_opportunity_merge.py` | base 轴间隔、默认是否开新段 |
| `test_price_factor_replayer.py` | 去噪并行回放：邻根合并、远段并行、涨停递补、钩子 override |
| `test_price_factor_deferred_exit.py` | 跌停顺延卖出；未平仓不再挡住后一段 |
| `test_price_factor_executor.py` | worker 读枚举、落盘 |
| `test_price_factor_job_builder.py` | bundle payload |
| `test_price_factor_enum_data.py` | 枚举目录加载 |
| `test_price_factor_report_manager.py` | 报告 |
| `test_price_factor_timeline.py` | 仿真窗口 |
| `test_price_factor_timeline_hooks.py` | timeline 钩子 |
