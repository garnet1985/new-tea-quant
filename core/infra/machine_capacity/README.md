# Machine Capacity（`infra.machine_capacity`）

为 New Tea Quant（简称 **NTQ**）提供本机 CPU / 内存容量探测，供 BacktestEngine 等调度器解析 worker 数与内存预算。对外门面类（Facade）为 `MachineInfo`；快照类型 `MachineCapacity` 见 `contracts`。词条见 [glossary.yaml](./glossary.yaml)。

## 适用场景

- 调度前根据 `performance` 配置计算可用 worker 与内存预算（含 `auto`）

## 模块依赖

无（可选 `psutil` 读取真实内存；缺失时用内置回退值）。

## 设计初衷

- **要解决的问题：** 把容量探测从 BacktestEngine 中抽成可复用原语。
- **明确不做：** 不读 `worker.json`、不做 dispatch plan、不执行进程池。

## 常见问题

**Q：该 import 什么？**  
A：`from core.infra.machine_capacity import MachineInfo`；类型 `from core.infra.machine_capacity.contracts import MachineCapacity`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
