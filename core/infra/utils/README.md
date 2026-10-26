# Utils（`infra.utils`）

**模块：** `infra.utils` · **版本：** `0.2.2`

## 简介

和业务无关的通用小工具。日期处理、类型转换、CSV / zip IO、确定性随机、Markdown 模板填充、本机时区——这些东西散在各模块会形成"互相 import"的蛛网，集中一处。

## 适用场景

- 模块里要写 CSV、打包 zip
- 算交易日偏移、生成确定性 UUID

## 模块依赖

无硬依赖（运行需 Python 标准库）

## 设计初衷

- **要解决的问题：** 通用小工具集中一处，避免各模块重复实现或互相依赖。
- **明确不做：** 不做业务工具（回测指标、因子计算等）；不做第三方库的薄代理（pandas、numpy 直接 import）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [架构](./docs/ARCHITECTURE.md)
- [术语表](./glossary.yaml)
- [快速开始](./QUICKSTART.md)
- [设计](./docs/DESIGN.md)
- [决策](./docs/DECISIONS.md)
