# Data Contract（`modules.data_contract`）

**模块：** `modules.data_contract` · **版本：** `0.4.3`

## 简介

声明式取数。上层模块（策略、回测、标签）只写"我要 XX 数据"，不用管底层是查表还是拼多源。模块把声明翻译成实际的数据加载。

## 适用场景

- 策略回测需要某列因子、某张表的某个 key，不想知道底层加载细节
- 标签计算需要多个数据源拼在一起，不想自己写 join

## 模块依赖

- `infra.project_context`：路径与配置
- `infra.utils`：通用工具
- `modules.data_manager`：底层数据读取

## 设计初衷

- **要解决的问题：** 把"要什么数据"和"怎么拿到"分开，上层只写声明。
- **明确不做：** 不缓存原始数据、不做业务调度。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
