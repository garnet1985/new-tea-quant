# Setup 设计

**版本：** `0.1.1`

## 设计点 1：安装域独立于 CLI

### 设计初衷

安装必须在尚无可用 CLI、甚至尚无 venv 时能跑（源码 zip / Docker / `install.py`）。

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 设计点 2：门面收口

对外只导出 `Setup`。`NewTeaQuantSetup`、`install_cli_runtime` 等为内部实现，步骤脚本可继续引用，产品代码与 CLI handlers 不应深挖。

## 设计点 3：CLI 与 UI 安装状态同一份

### 设计初衷

`install.py` 不询问 userspace / 数据库，但开始前要同意使用条款；这两项不能被静默丢掉。UI 向导刷新后必须看到同一完成态。

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）