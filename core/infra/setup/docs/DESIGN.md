# Setup 设计

**版本：** `0.1.0`

## 设计点 1：安装域独立于 CLI

### 设计初衷

安装必须在尚无可用 CLI、甚至尚无 venv 时能跑（源码 zip / Docker / `install.py`）。

### 结论

- 安装逻辑只写在 `core/infra/setup/`
- `cli.py` / `devcli.py` 安装相关只调用 `Setup.*`；应用升级走 `userspace/system/updater` / `Updater`
- 禁止 `infra.setup` import `core.infra.cli`
- 禁止 setup 实现升级编排（见 `infra.updater`）
- 产物 zip 落在仓库根 `init_userspace/`、`init_data/`

## 设计点 2：门面收口

对外只导出 `Setup`。`NewTeaQuantSetup`、`install_cli_runtime` 等为内部实现，步骤脚本可继续引用，产品代码与 CLI handlers 不应深挖。
