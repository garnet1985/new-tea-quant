# Decisions — infra.cli

## D1：双入口，不合成一个二进制

用户命令与开发命令受众不同；短别名已冲突（如 `ex`）。保留 `cli.py` / `devcli.py`，代码合并到 `infra.cli`。

## D2：只 export `Cli`

符合 CORE_MODULE_STANDARDS Facade；禁止导出 `main` / `expand_argv` 等自由函数。调用一律 `Cli.user.*` / `Cli.dev.*` / `Cli.shared.*`。

## D3：shared 是 namespace 不是独立包产品

argv 脚手架被两端复用，但不是第三套 CLI；挂在 `Cli.shared` 下。

## D4：无兼容层

删除 `infra.devcli` 与函数式公开导出；调用方一次性改到 `Cli`。
