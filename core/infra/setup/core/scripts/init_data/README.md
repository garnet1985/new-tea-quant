# init_data — 演示数据包导出

将本地 DB 打成 **`core/infra/setup/core/steps/import_data`** 可导入的演示数据 zip。

## 入口

```bash
python devcli.py ex
python -m core.infra.setup.core.scripts.init_data --help
```

默认写入 **`initialization/data/data_demo.zip`**（固定名，供安装 + 提交 Git，每次覆盖）。

可选 `python dev-cli.py -ex -- --tagged` 额外生成 `data_v*.zip` 副本（已 ignore，勿 commit）。详见 `initialization/data/README.md`。

## 默认参数

| 项 | 值 |
|----|-----|
| 股票抽样 | 300 只（分层）；`TARGET_STOCK_COUNT <= 0` 或 `--stock-count 0` 为全市场 |
| 日期窗 | 20250101 ~ 20260101 |
| 季度窗 | 2025Q1 ~ 2025Q4 |

## 不导出的表

运行时/框架生成数据，见 `config.EXCLUDED_GENERATED_TABLES`：`sys_cache`、`sys_meta_info`、tag 四表、`sys_strategy_workbench_snapshot` 等。

## 配置

- [`config.py`](config.py)：导出表清单与上表默认值（改这里即可）
- [`stock_pool.py`](stock_pool.py)：按 **上市状态 × 板块 × 交易所** 分层抽样

## 输出命名

`data_v{core_version}_{stock_count}_{from_date}_{to_date}.zip`

例如 `data_v0.3.2_300_20250101_20260101.zip`（版本来自 `core/system.json`）。

## 常用参数

| 参数 | 说明 |
|------|------|
| `--stock-count N` | 抽样股票数 |
| `--start-date` / `--end-date` | 时序数据日期窗 |
| `--skip-sample` | 不抽样，导出全市场（体积大） |
| `--tables a,b` | 只导出指定表 |
| `-o path.zip` | 指定输出路径 |
