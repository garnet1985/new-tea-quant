# analyzer — TODO

回测闭环的最后一环：解释这一次 version 的 inputs 与 outputs。
从空的 `modules.analysis` 收回本包；对外走 `Strategy.analyze`，不另起顶层模块。

已拍板

- 按 enum / price / portfolio **分三层**归因（与工作台 step 对齐）
- 产物写在被解释的 version 目录：`simulations/<kind>/<vid>/analysis/`（和回测一起 prune）
- `settings.analysis.enabled` 控制回测后自动跑；不进指纹
- CLI / BFF 在 simulate 成功后调用；也可单独跑
- 不是 BE 引擎：不要 JobBuilder / Pipeline / Timeline
- reporter / analyzer **同一套 input**：`services.artifacts.ArtifactStore` 读一次、进程内缓存

输入：该层产物 + 上游 `enum_version_id` + `investment_id` join 的 `signal_snapshots`
输出：不要重复 overall 的胜率/净值

factor 模块若要解释的是**一次策略回测 version**，调用 `Strategy.analyze` 即可。
因子研究（IC / 滚动 / 挖掘）不是本包的问题。

---

## 分段（当前：第 1 步完成；下一步接线）

1. **产物 service**（完成）— `services.artifacts.ArtifactStore`：定位 version、读/写表、prune、进程内缓存。调用方走这一套，无平行遗留读盘代码。
2. **接线** — `Strategy.analyze`；`settings.analysis.enabled`；CLI `sa`；`se`/`sp`/`so` 与 BFF 成功后按开关调用。
3. **enum 归因** — collector join；清单 + 决定空间；写 `analysis/source.json` + `report.json`。
4. **price / portfolio 槽位** — `source.json` 三层都有；算法可后补，不要 404。

不做：搬 `report_manager`、删 `modules.analysis`、IC/滚动、把 join 塞进 ArtifactStore。
