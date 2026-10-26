# infra.setup — 决定

**版本：** `0.1.1`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：设计点 1：安装域独立于 CLI

- 安装逻辑只写在 `core/infra/setup/`
- `cli.py` / `devcli.py` 安装相关只调用 `Setup.*`；应用升级走 `userspace/system/updater` / `Updater`
- 禁止 `infra.setup` import `core.modules.cli`
- 禁止 setup 实现升级编排（见 `infra.updater`）
- 产物 zip 落在 `initialization/userspace/`、`initialization/data/`

---

## DEC-02：设计点 3：CLI 与 UI 安装状态同一份

- `.ntq/setup-runtime.json` 的 `isReady` 是向导完成态的唯一事实来源
- CLI 可带 `--userspace` / `--db`（及连接参数）；省略走默认；带了就必须用；失败即停
- CLI 跑完写入同一份 `setup-runtime.json`；UI 向导跑完同时 `mark_cli_ready`


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
