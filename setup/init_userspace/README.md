# init_userspace

在这里放置干净的 userspace 初始化包（zip）。

- 默认文件名：`userspace.zip`
- `init_userspace` 步骤会读取该 zip 并解压到目标目录
- 若未指定目标目录，默认解压到项目根目录下的 `userspace/`

## 维护 zip 源树

仓库内可编辑的 **源目录** 为与本 README 同级的 `userspace/`（内含 `strategies/example`、`adapters` 等）。更新后在本目录下重新打包为 `userspace.zip` 即可供安装步骤使用；`Opportunity` 等类型请自 `core.modules.strategy.engines.shared.data_classes` 导入（勿再使用已移除的 `core.modules.strategy.models`）。

### ``updater/``（升级 bootstrap）

**版本库源树**：仓库根下 **`setup/updater/`**（可编辑、可跑 pytest；**不要**把 ``__test__`` 打进 zip）。

打 **init userspace zip** 时，将 ``setup/updater/`` 下的运行时文件（``pipeline.py``、``helper.py``、``run_apply.py``、``README.md``）放进包内 ``updater/``，解压后为 **`userspace/updater/`**。应用升级会替换 ``core/``、``setup/`` 等，**不能把升级编排放在那些路径**；运行时说明见解压后的 **`userspace/updater/README.md`**。

**测试**：在 **`core/infra/db/__test__/test_updater_migration_spawn.py`**（``pytest`` 的 ``testpaths=core`` 会收集），导入 ``setup/updater/helper.py``。
