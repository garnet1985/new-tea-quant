# rolling 测试索引

**模块：** `modules.strategy`  
**版本：** `0.10.0`

| 测试 | 覆盖 |
|------|------|
| `test_rolling_report.py` | `rolling.py` 窗口校验；日历重叠；对照差值不含账户总收益 |
| `services/artifacts/__test__/test_version_meta.py` | `{主号}-roll{n}` 不进版本列表、不占用归因副本号、不推进 `next_version_id` |
