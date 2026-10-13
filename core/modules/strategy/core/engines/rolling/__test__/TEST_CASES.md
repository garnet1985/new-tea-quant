# rolling 测试索引

**模块：** `modules.strategy`  
**版本：** `0.11.0`

| 测试 | 覆盖 |
|------|------|
| `test_rolling_report.py` | `rolling.py` 窗口校验；日历重叠；对照差值不含账户总收益 |
| `test_rolling_readiness.py` | 三层完成且 `rolling.py` 可用，滚动测试按钮才可点 |
| `services/artifacts/__test__/test_version_meta.py` | `{主号}-roll{n}` 不进版本列表、不占用归因副本号、不推进 `next_version_id` |
