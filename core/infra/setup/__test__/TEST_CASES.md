# Setup 公开 API 用例（与 test_api.py 对齐）

**版本：** `0.1.1`  
- 包根仅导出 `Setup`
- `env.repo_root()` 指向含 `core/system.json` 的仓库根
- `runtime.cli_install_scope()` 返回 full / deps_only / none
- `runtime.pipeline_ready()` 读取 `.ntq/setup-runtime.json` 的 `isReady`
- `meta.load_step_meta()` 返回 list
- `install.py --userspace / --db …` 非交互参数；省略则默认 userspace + DuckDB
