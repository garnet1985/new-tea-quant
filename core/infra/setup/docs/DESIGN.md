# Setup 设计

**版本：** `0.1.1`

## 设计点 1：安装域独立于 CLI

### 设计初衷

安装必须在尚无可用 CLI、甚至尚无 venv 时能跑（源码 zip / Docker / `install.py`）。

### 结论

- 安装逻辑只写在 `core/infra/setup/`
- `cli.py` / `devcli.py` 安装相关只调用 `Setup.*`；应用升级走 `userspace/system/updater` / `Updater`
- 禁止 `infra.setup` import `core.modules.cli`
- 禁止 setup 实现升级编排（见 `infra.updater`）
- 产物 zip 落在 `initialization/userspace/`、`initialization/data/`

## 设计点 2：门面收口

对外只导出 `Setup`。`NewTeaQuantSetup`、`install_cli_runtime` 等为内部实现，步骤脚本可继续引用，产品代码与 CLI handlers 不应深挖。

## 设计点 3：CLI 与 UI 安装状态同一份

### 设计初衷

`install.py` 非交互，但 userspace / 数据库不能被静默丢掉；UI 向导刷新后必须看到同一完成态。

### 结论

- `.ntq/setup-runtime.json` 的 `isReady` 是向导完成态的唯一事实来源
- CLI 可带 `--userspace` / `--db`（及连接参数）；省略走默认；带了就必须用；失败即停
- CLI 跑完写入同一份 `setup-runtime.json`；UI 向导跑完同时 `mark_cli_ready`
