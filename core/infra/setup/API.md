# Setup API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.4.4`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Setup`；类型从 [`contracts.py`](./contracts.py) 导入，或经 `Setup.types`。  
**边界：** 安装逻辑只在 `setup/`；`cli.py` / `devcli.py` / `install.py` / `launcher.py` / BFF 只调用本门面。

---

## Setup

**描述：** 安装域门面类（Facade）— 下挂 `env` / `runtime` / `artifacts` / `meta` / `trace` / `types`

### env

**描述：** 仓库路径、venv、工作目录

#### repo_root

`Setup.env.repo_root() -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 仓库根目录

#### venv_python / in_virtualenv

`Setup.env.venv_python() -> Path`  
`Setup.env.in_virtualenv() -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`

#### ensure_sys_path / to_root_dir

`Setup.env.ensure_sys_path() -> None`  
`Setup.env.to_root_dir() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 将仓库根加入 `sys.path`；`chdir` 到仓库根

#### ensure_venv

`Setup.env.ensure_venv(entry_script: str | Path | None = None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 不在 venv 中则创建 `venv/` 并用其解释器 `exec` 当前入口脚本

#### ensure_venv_for_setup_step

`Setup.env.ensure_venv_for_setup_step(script_path: str | Path) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** `core/infra/setup/core/steps/*/install.py` 直接执行时切到项目 venv

#### requirements_txt / ui_bff_requirements / ui_fed_root

`Setup.env.requirements_txt() -> Path`  
`Setup.env.ui_bff_requirements() -> Path`  
`Setup.env.ui_fed_root() -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`

---

### runtime

**描述：** 安装状态与 CLI / UI 安装编排

#### needs_install

`Setup.runtime.needs_install(profile: "cli" | "ui") -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 状态文件、core 版本、userspace、runtime 成功标记、依赖指纹

#### cli_install_scope

`Setup.runtime.cli_install_scope() -> "full" | "deps_only" | "none"`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`

#### install_cli / ensure_cli_install

`Setup.runtime.install_cli(*, force: bool = False) -> None`  
`Setup.runtime.ensure_cli_install() -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 跑 CLI 安装步骤；`ensure_cli_install` 经根目录 `install.py`（user CLI 自动触发）

#### install_ui / check_ui_prerequisites / launch_ui / set_ui_dev_mode

`Setup.runtime.install_ui(*, force: bool = False) -> None`  
`Setup.runtime.check_ui_prerequisites() -> tuple[bool, str]`  
`Setup.runtime.launch_ui() -> None`  
`Setup.runtime.set_ui_dev_mode(enabled: bool) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`

#### fed_build_ready / userspace_ready / mark

`Setup.runtime.fed_build_ready() -> bool`  
`Setup.runtime.userspace_ready() -> bool`  
`Setup.runtime.mark(profile, *, success: bool, failed_step_id="", fingerprints=None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`

---

### artifacts

**描述：** 安装产物工厂（写入 `initialization/userspace/`、`initialization/data/`）

#### package_userspace

`Setup.artifacts.package_userspace(*, write_zip: bool = True) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 同步仓库 `userspace/` → `initialization/userspace/` 并可选写 zip；`0` 成功

#### export_demo_data

`Setup.artifacts.export_demo_data(argv: Sequence[str] | None = None) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 导出演示数据包到 `initialization/data/`；`argv` 同 `python -m core.infra.setup.core.scripts.init_data`

---

### meta

#### load_step_meta

`Setup.meta.load_step_meta(*, ui_only: bool = True) -> list[dict]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 读取 `core/infra/setup/core/steps/*/meta.json`，按依赖拓扑排序

---

### trace

`Setup.trace.install_complete(*, success: bool, entry: "ui" | "cli", error_code=None) -> None`  
`Setup.trace.app_start(*, entry: "ui" | "cli" | "devcli") -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 失败不影响安装；勿上报异常原文

---

### types

与 [`contracts.py`](./contracts.py) 同源：`InstallProfileName`、`CliInstallScope`、`InstallEntry`、`AppEntry`。
