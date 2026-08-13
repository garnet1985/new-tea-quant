# init_userspace

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
export NTQ_USERSPACE_ROOT="$(git rev-parse --show-toplevel)/setup/init_userspace/userspace"

# 方式 2：写入仓库根 .ntq/userspace-path.json（见 userspace-path.dev.example.json，该目录通常 gitignore）
```

打包前在本目录重新生成 `userspace.zip`（见上节「维护 zip 源树」）。

**推荐（自动清理密钥与缓存）：**

```bash
python dev-cli.py -userspace
# 或发布检查通过后一并打包：
python dev-cli.py -p -v0.4.0 -userspace
```

会从仓库根 `userspace/` 复制到本目录 `userspace/`，删除数据库连接、数据源 token、`.ntq`、策略 `results/`、`extensions/data_source/handlers/` 下运行时 `.csv` 等，并同步 `setup/core/updater/` 到 `userspace/system/updater/`，最后写入 `userspace.zip` 与 `userspace.meta.json`。

### ``updater/``（升级 bootstrap）

**版本库源树**：仓库根下 **`setup/core/updater/`**（可编辑、可跑 pytest；**不要**把 ``__test__`` 打进 zip）。

打 **init userspace zip** 时，将 ``setup/core/updater/`` 下的运行时文件（``pipeline.py``、``helper.py``、``run_apply.py``、``README.md``）放进包内 ``updater/``，解压后为 **`userspace/updater/`**。应用升级会替换 ``core/``、``setup/`` 等，**不能把升级编排放在那些路径**；运行时说明见解压后的 **`userspace/updater/README.md`**。

**测试**：在 **`core/infra/db/__test__/test_updater_migration_spawn.py`**（``pytest`` 的 ``testpaths=core`` 会收集），导入 ``setup/core/updater/helper.py``。
