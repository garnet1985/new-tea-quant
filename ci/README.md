# CI 脚本

仅供 GitHub Actions / 本地复现 CI 验收使用，**不是**运行时 API，也不是 `devcli pack` 发布闸门。

| 脚本 | Workflow | 作用 |
|------|----------|------|
| [`smoke_fresh_install.py`](./smoke_fresh_install.py) | `.github/workflows/ci.yml` → `smoke-fresh-install` | 模拟源码 zip 冷启动：`install.py` → `cli.py se` |

本地复现（在已解压的项目根）::

```bash
python ci/smoke_fresh_install.py
```

与下列区分：

- **dev CLI**（`core/infra/cli/dev/scripts/`）：本地维护 + 可被 CI 调用（如 `dependency_risk`、`minimal_import_check`），也常挂在 `devcli` / `pack`
- **`TaskGuard`**（`infra.task_guard`）：长任务互斥，不放 CI 编排
