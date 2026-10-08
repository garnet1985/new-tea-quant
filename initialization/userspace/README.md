# initialization/userspace

安装用的 userspace 初始化包放在这里。

| 文件 | 说明 |
|------|------|
| `userspace.zip` | **固定文件名**。`python devcli.py pu` 每次覆盖 |
| `userspace.meta.json` | 记录打包时的 core 版本、zip 大小、git rev |
| `userspace/` | 打包前的可编辑副本（**gitignore**）。`devcli pu` 从仓库根 `userspace/` 重新生成 |

仓库里日常改的是根目录 `userspace/`（策略、标签、数据源、适配器等）。本目录下的 `userspace/` 只是打包中间树，不要把它当成源。

## 重新打包

```bash
python devcli.py pu
```

不写 zip、只同步目录时：

```bash
python devcli.py pu --no-zip
```

发布检查通过后一并打包：

```bash
python devcli.py p -core_v0.5.1 --package-userspace
```

`pu` 会先把升级编排写进仓库根 `userspace/system/updater/`（`Updater.runtime.sync_orchestrator`），再复制到本目录并清理密钥、数据库、`.ntq`、策略 `results/`、数据源 handler 下的运行时 `.csv`，最后打成 `userspace.zip`。

## 本地开发：直接指向源树

运行时默认用仓库根 `userspace/`。若要改用本目录下的副本，优先级高于仓库根：

```bash
export NTQ_USERSPACE_ROOT="$(git rev-parse --show-toplevel)/initialization/userspace/userspace"
```

也可以把绝对路径写入仓库根 `.ntq/userspace-path.json`（该目录通常 gitignore）。

策略钩子与 `Opportunity` 从 `core.modules.strategy.contracts` 导入。
