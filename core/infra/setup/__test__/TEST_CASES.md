# Setup 公开 API 用例（与 test_api.py 对齐）

- 包根仅导出 `Setup`
- `env.repo_root()` 指向含 `core/system.json` 的仓库根
- `runtime.cli_install_scope()` 返回 full / deps_only / none
- `meta.load_step_meta()` 返回 list
