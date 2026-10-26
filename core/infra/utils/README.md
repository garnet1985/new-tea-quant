# Utils（`infra.utils`）

**模块：** `infra.utils` · **版本：** `0.2.2`

与业务无关的通用工具：日期、类型 / DataFrame、CSV / 归档 IO、确定性随机、Markdown 模版填充、本机区域。对外门面为 `Utils`（按 namespace 组织）。

## 适用场景

- 各模块做 CSV 落盘 / zip 打包时用 `Utils.io`
- 时间差、交易日偏移等日期计算用 `Utils.date`
- 生成确定性 UUID（用于策略指纹等）用 `Utils.types`

## 模块依赖

无硬依赖
## 设计初衷

- **要解决的问题：** 通用小工具散落在各模块会形成"内部又依赖内部"的蛛网，收一处即可。
- **明确不做：** 不做业务工具（回测指标、因子计算等）；不做第三方库的薄代理（pandas、numpy 直接 import）。

## 常见问题

**Q：该 import 什么？**
A：`from core.infra.utils import Utils`；具体 namespace 见 [API.md](./API.md)。

## 相关文档

- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
