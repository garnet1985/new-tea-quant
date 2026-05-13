# init_userspace

在这里放置干净的 userspace 初始化包（zip）。

- 默认文件名：`userspace.zip`
- `init_userspace` 步骤会读取该 zip 并解压到目标目录
- 若未指定目标目录，默认解压到项目根目录下的 `userspace/`

## 维护 zip 源树

仓库内可编辑的 **源目录** 为与本 README 同级的 `userspace/`（内含 `strategies/example`、`adapters` 等）。更新后在本目录下重新打包为 `userspace.zip` 即可供安装步骤使用；`Opportunity` 等类型请自 `core.modules.strategy.engines.shared.data_classes` 导入（勿再使用已移除的 `core.modules.strategy.models`）。

### ``updater/``（升级 bootstrap）

目录 **`updater/`**（与本 README 同级）为 **init userspace zip 必须包含** 的内容之一：解压后为 **`userspace/updater/`**，内含 ``pipeline.py``、``run_apply.py``（占位）。应用升级会替换 ``core/``、``setup/`` 等，**不能把升级编排放在那些路径**；详见 **`userspace/updater/README.md`**（运行时文档）。
