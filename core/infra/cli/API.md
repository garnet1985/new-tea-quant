# CLI API 文档

**版本：** `0.4.2`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**；内部私有实现不写入。  
> 所列入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

---

## Cli

**描述：** 命令行门面类（Facade）— 下挂 `user` / `dev` / `shared` 命名空间（namespace）

### user

**描述：** 终端用户 CLI（`cli.py`）

#### ensure_venv

`Cli.user.ensure_venv(entry_file: str) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.2`
- **描述：** 仅做 venv 重入（轻量；入口脚本可在拉起重依赖前先调用）
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `entry_file` | `str` | 入口脚本路径，通常传 `__file__` |

- **返回值：** `None`
- **举例：**

```python
from core.infra.cli import Cli

Cli.user.ensure_venv(__file__)
```

#### bootstrap

`Cli.user.bootstrap(entry_file: str) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** venv 重入与 install 门闸（仅 user 入口需要）
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `entry_file` | `str` | 入口脚本路径，通常传 `__file__` |

- **返回值：** `None`
- **举例：**

```python
from core.infra.cli import Cli

Cli.user.bootstrap(__file__)
```

#### main

`Cli.user.main(argv: list[str] | None = None) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 解析 argv 并执行用户命令
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `argv` (可选) | `list[str] \| None` | 默认 `sys.argv[1:]` |

- **返回值：** `int` — 进程退出码
- **举例：**

```python
from core.infra.cli import Cli

raise SystemExit(Cli.user.main())
```

---

### dev

**描述：** 开发 / 运维 CLI（`devcli.py`）

#### main

`Cli.dev.main(argv: list[str] | None = None) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 解析 argv 并执行开发命令
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `argv` (可选) | `list[str] \| None` | 默认 `sys.argv[1:]` |

- **返回值：** `int` — 进程退出码
- **举例：**

```python
from core.infra.cli import Cli

raise SystemExit(Cli.dev.main())
```

---

### shared

**描述：** 双入口共用的 argv 脚手架（非第三套 CLI）

#### expand_argv

`Cli.shared.expand_argv(argv, *, short_to_long, long_commands, default_command="version", version_argv=None, after_expand=None) -> list[str]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 将首 token 的短命令别名展开为长命令名；空 argv 或仅 version 旗标时回落到 `default_command`
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `argv` | `Sequence[str]` | 原始参数（不含程序名） |
| `short_to_long` | `Mapping[str, str]` | 短别名 → 长命令名 |
| `long_commands` | `frozenset[str]` | 合法长命令集合 |
| `default_command` (可选) | `str` | 默认 `"version"` |
| `version_argv` (可选) | `frozenset[str] \| None` | 默认 `{-v, --version}` |
| `after_expand` (可选) | `Callable[[list[str]], list[str]] \| None` | 展开后的钩子；默认不调用 |

- **返回值：** `list[str]` — 规范化后的 argv
- **举例：**

```python
from core.infra.cli import Cli

Cli.shared.expand_argv(
    ["sp", "-f"],
    short_to_long={"sp": "strategy_price_factor"},
    long_commands=frozenset({"strategy_price_factor"}),
)
```

#### is_help_argv

`Cli.shared.is_help_argv(argv: Sequence[str]) -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 首 token 是否为 `-h` / `--help` / `help`
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `argv` | `Sequence[str]` | 参数列表 |

- **返回值：** `bool`
- **举例：**

```python
from core.infra.cli import Cli

Cli.shared.is_help_argv(["-h"])  # True
```

#### aliases_for

`Cli.shared.aliases_for(short_to_long: Mapping[str, str], long_name: str) -> list[str]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 给定长命令名，返回对应短别名列表（排序）
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `short_to_long` | `Mapping[str, str]` | 短别名 → 长命令名 |
| `long_name` | `str` | 长命令名 |

- **返回值：** `list[str]` — 短别名（已排序）
- **举例：**

```python
from core.infra.cli import Cli

Cli.shared.aliases_for(
    {"sp": "strategy_price_factor", "spf": "strategy_price_factor"},
    "strategy_price_factor",
)
```
