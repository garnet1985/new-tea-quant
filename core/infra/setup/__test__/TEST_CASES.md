# Setup 公开 API 用例（与 test_api.py 对齐）

**模块：** `infra.setup` · **版本：** `0.2.1`

**最低支持核心版本：** `>=0.5.0`

- 包根仅导出 `Setup`
- `env.repo_root()` 指向含 `core/system.json` 的仓库根
- `runtime.cli_install_scope()` 返回 full / deps_only / none
- `runtime.pipeline_ready()` 读取 `.ntq/setup-runtime.json` 的 `isReady`
- `runtime.bind_install_progress_dir` / `read_import_progress` 供 BFF / job_pipeline
- `meta.load_step_meta()` 返回 list
- `install.py --userspace / --db …` 非交互参数；省略则默认 userspace + DuckDB
