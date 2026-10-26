# infra.trace — 决定

**版本：** `0.1.2`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：决策摘要

## 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅静态 Facade | 无需实例化 |
| 默认开关 | opt-in，默认关 | 隐私；同意存 `system/config` 而非 `.ntq` |
| 默认 URL | `ntq_external` 登记 | trace 不内置官网地址；模块不在则不发送 |
| 覆盖 | env > `trace.json` > defaults | 运维可改目标站，无需改代码 |
| track | 立刻 POST；失败入队 | 短进程也能尽量送达 |
| queue | 只写本地队列 | 非阻塞批量 |
| send | 按预算发送队列 | 主动推送 / 退出收尾 |
| 体字段 | 脱敏 | 禁止路径/token |
| 公开稳定性 | 最高 `beta` | core `0.x` |


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
