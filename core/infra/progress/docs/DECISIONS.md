# infra.progress — 决定

**版本：** `0.2.1`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：设计点 1：所有业务共用一份当前进度

- **采用：** 方案 A
- **理由：** 界面只需要当前正在跑的那一次。错误和结果仍由各业务模块自己的记录保存。
- **影响：** 后开始的任务覆盖前一份进度。
- **后续：** 设计点 2 改为一个根节点一份文件。本决定不再使用。

---

---

## DEC-02：设计点 2：同一种节点，按 id 查找

- **采用：** 方案 A
- **理由：** 加字段时只改一种节点。tick 只带 id。
- **影响：** 有子节点的 ratio 来自子节点的 weight；叶子才用 done / total。

---

---

## DEC-03：设计点 3：写盘可以合并

- **采用：** 方案 A
- **理由：** 解析器不需要每一次 tick 都已经在磁盘上。日志仍在调用当次打印。
- **影响：** 没有定时器去推进进度。

---

## DEC-04：设计点 4：频道快照走 Progress.channel

- **采用：** 方案 A
- **理由：** Facade 只导出 `Progress`；infra 不写业务 channel 名；tag 可直连 `Progress.channel`，不必依赖 strategy。
- **影响：** strategy 若要包一层约定，放在本模块 `core/`（如 `ProgressRecorder`），不经 infra 包根导出。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
