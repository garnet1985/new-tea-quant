# Design — infra.cli

## 短别名

首 token 若在 `SHORT_TO_LONG` 中则替换为长命令，再交给 argparse。空 argv / `-v` / `--version` → `version`。

dev 的 `pack` 额外支持 `-core_vX.Y.Z` → `--version X.Y.Z`。

## Bootstrap（仅 user）

1. 若不在 venv 且存在 `venv/`，`os.execv` 重入。
2. 非 early 命令时按需跑 `install.py`。
3. early：`update` / `version` / export|import strategy、help、`-n` 新建。

## 命令分发

- user：`UserRunner.main` → early handlers 或 `CliApp` + `execute`。
- dev：argparse `set_defaults(handler=...)` → 直接调用 handler。
