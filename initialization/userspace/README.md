# initialization/userspace

在这里放置干净的 userspace 初始化包（zip）。

| 文件 | 说明 |
|------|------|
| `userspace.zip` | **固定文件名**，`python dev-cli.py -userspace` 每次覆盖 |
| `userspace.meta.json` | 记录打包时的 core 版本、zip 大小、git rev（便于核对） |
| `userspace/` | 可编辑源树（开发时可指向，不必每次打 zip） |

## 维护 zip 源树

仓库内可编辑的 **源目录** 为与本 README 同级的 `userspace/`（内含 `strategies/example`、`adapters` 等）。更新后在本目录下重新打包为 `userspace.zip` 即可供安装步骤使用；`Opportunity` 等类型请自 `core.modules.strategy.engines.shared.data_classes` 导入（勿再使用已移除的 `core.modules.strategy.models`）。

### 本地开发：直接使用源树（不打 zip）

编辑本目录下 `userspace/` 后，让运行时指向该目录（优先级高于项目根 `userspace/`）：

```bash
# 方式 1：环境变量（推荐，可写入 shell 配置）
export NTQ_USERSPACE_ROOT="$(git rev-parse --show-toplevel)/initialization/userspace/userspace"

# 方式 2：写入仓库根 .ntq/userspace-path.json（见 userspace-path.dev.example.json，该目录通常 gitignore）
```

打包前在本目录重新生成 `userspace.zip`（见上节「维护 zip 源树」）。

**推荐（自动清理密钥与缓存）：**

```bash
python dev-cli.py -userspace
# 或发布检查通过后一并打包：
python dev-cli.py -p -v0.4.0 -userspace
```

会从仓库根 `userspace/` 复制到本目录 `userspace/`，删除数据库连接、数据源 token、`.ntq`、策略 `results/`、`extensions/data_source/handlers/` 下运行时 `.csv` 等。`devcli pu` 会先调用 `Updater.runtime.sync_orchestrator` 写入 `userspace/system/updater/`，再打包 zip。

### ``userspace/system/updater/``（升级 bootstrap）

**源码**：[`core/infra/updater/core/orchestrator/`](core/infra/updater/core/orchestrator/)（可编辑、可跑 pytest；**不要**把 ``__test__`` 打进 zip）。

运行时必须在 **`userspace/system/updater/`**：升级会替换 `core/`，不能在那棵树上执行编排。同步入口：`Updater.runtime.sync_orchestrator`。

**测试**：[`core/infra/updater/core/orchestrator/__test__/`](core/infra/updater/core/orchestrator/__test__/)。
