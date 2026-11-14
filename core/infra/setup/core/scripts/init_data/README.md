# init_data — 安装/会员数据包导出

将本地 DB 打成 **`core/infra/setup/core/steps/import_data`** 可导入的 zip。

## 入口

```bash
python devcli.py ex              # 显示帮助（不导出）
python devcli.py ex --demo       # 公开安装包
python devcli.py ex --member     # 注册会员包
python devcli.py ex --full       # 全市场全历史
python -m core.infra.setup.core.scripts.init_data --help
```

默认按预设写入 **`userspace/.ntq/packages/{demo|member|full}/data_*.zip`**（与安装下载共用；userspace 须已存在）。
安装下载源在官网 `ntq_data/assets/install/`——导出后请手动复制 zip + meta 到该目录并部署。

可选 `python devcli.py ex --demo --tagged` 额外生成 `data_v*` 副本。

## 预设

| 预设 | 股票池 | 日期窗 | 用途 |
|------|--------|--------|------|
| `--demo` | 约 300 只分层抽样 | 默认三年窗 | 公开安装演示包 |
| `--member` | 全市场 | 默认三年窗 | 注册会员包（体积约数百 MB～1GB） |
| `--full` | 全市场 | 忽略日期窗（全历史） | 全量备份级（可达数 GB） |

默认日期窗：`20230101` ~ `20251231`；季度窗：`2023Q1` ~ `2025Q4`。  
ST 时段按与窗相交导出；复权因子会在窗起点补锚点。

## 不导出的表

运行时/框架生成数据，见 `config.EXCLUDED_GENERATED_TABLES`：`sys_cache_kv`、`sys_meta_info`、tag 四表等。

## 配置

- [`config.py`](config.py)：导出表清单与日期/抽样默认值（改这里即可）
- [`stock_pool.py`](stock_pool.py)：按 **上市状态 × 板块 × 交易所** 分层抽样

## 输出命名

`data_v{core_version}_{stock_count}_{from_date}_{to_date}.zip`

例如 `data_v0.5.0_300_20230101_20251231.zip`（版本来自 `core/system.json`）。

## 常用高级参数

| 参数 | 说明 |
|------|------|
| `--end-date YYYYMMDD` | 覆盖窗终点（会员包常扩到数据最新日） |
| `--stock-count N` | 覆盖抽样数；`<= 0` 表示全市场 |
| `--skip-sample` | `--demo` 下强制全市场 |
| `--no-date-filter` | 忽略日期窗（旧 `--full` 语义；`--full` 预设已隐含） |
| `--tagged` | 额外写 `data_v*` 副本 |
| `-o path.zip` | 指定输出路径 |
