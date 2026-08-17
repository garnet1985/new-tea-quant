# reporter — TODO

把现有各引擎 `report_manager/` 收拢到这里（定制化报告的唯一落点）。

现状仍在用，先不要搬代码：

- `shared/services/report_manager`（`BaseReportManager`）
- `enumerator/common/report_manager`
- `price_factor/report_manager`
- `portfolio/report_manager`
- `scanner/report_manager`

约定：reporter 只描述「结果长什么样」；归因不进本包（见 `engines/analyzer`）。

读盘走 `services.artifacts.ArtifactStore`（与 analyzer 同一套 input、同一进程缓存）。收拢本包时不要再各自拼路径 / 读 CSV。
