# PostProcess（`modules.post_process`）

**模块：** `modules.post_process` · **版本：** `0.3.0`

## 简介

策略扫描完，发现了机会，接下来怎么分发？这个模块管这事儿。机会先被规成统一格式（哪只股票、什么价位），然后跑用户配置的各条后处理——通知微信、发邮件、对接本地 Broker 模拟下单，想接啥都行。

## 适用场景

- 扫描出一批机会，想自动推送到微信或邮件
- 扫描出机会后，直接喂给本地 Broker 做模拟下单验证

## 模块依赖

- `infra.project_context`：定位 userspace 下的后处理配置目录

## 设计初衷

- **要解决的问题：** 扫描结果怎么分发不该写死在策略里。Strategy 只管产机会，后处理怎么搞由用户自己配。
- **明确不做：** 后处理的 Adapter 是无序集合，不是流水线；不做 Adapter 之间的数据拼接（各 Adapter 独立跑）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [快速开始](./QUICKSTART.md)
- [架构](./docs/ARCHITECTURE.md)
- [出口协议](./docs/PROTOCOL.md)
- [PostProcessor](./docs/POST_PROCESSOR.md)
- [术语表](./glossary.yaml)
- [设计](./docs/DESIGN.md)
- [决策](./docs/DECISIONS.md)
