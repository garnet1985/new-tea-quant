# init_userspace

在这里放置干净的 userspace 初始化包（zip）。

- 默认文件名：`userspace.zip`
- `init_userspace` 步骤会读取该 zip 并解压到目标目录
- 若未指定目标目录，默认解压到项目根目录下的 `userspace/`

## 维护 zip 源树

仓库内可编辑的 **源目录** 为与本 README 同级的 `userspace/`（内含 `strategies/example`、`adapters` 等）。更新后在本目录下重新打包为 `userspace.zip` 即可供安装步骤使用；`Opportunity` 等类型请自 `core.modules.strategy.engines.shared.data_classes` 导入（勿再使用已移除的 `core.modules.strategy.models`）。
