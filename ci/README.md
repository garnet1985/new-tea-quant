# CI 脚本

仅供 GitHub Actions / 本地复现 CI 验收使用，**不是**运行时 API，也不是 `devcli pack` 发布闸门。

| 脚本 | Workflow | 作用 |
|------|----------|------|
| [`smoke_fresh_install.py`](./smoke_fresh_install.py) | `.github/workflows/ci.yml` → `smoke-fresh-install` | 模拟源码 zip 冷启动：`install.py` → 解析首个已启用策略 → `cli.py se` |

本地复现（在已解压的项目根）::

```bash
python ci/smoke_fresh_install.py
python ci/smoke_fresh_install.py --strategy dual_ma   # 可选：写死策略
```

与下列区分：

- **dev CLI**（`core/modules/cli/dev/scripts/`）：本地维护 + 可被 CI 调用（如 `dependency_risk`、`minimal_import_check`），也常挂在 `devcli` / `pack`
- **`JobPipeline`**（`infra.job_pipeline`）：长任务互斥与队列，不放 CI 编排
