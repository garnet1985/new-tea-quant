# quick_tools

本地开发脚本（非 `setup/` 安装职责）。入口推荐仓库根目录 **`devcli.py`**：

| devcli | 脚本 |
|--------|------|
| `ic` | `minimal_import_check.py` |
| `cgc` | `dev_cache.clear_userspace_ntq_dir` |
| `csc` | `dev_cache.clear_simulation_cache_all` |
| `p -core_vX.Y.Z` | `publish_prep.py`（版本/new_features 自 CHANGELOG 同步、徽章、module_info、pytest） |
| `ex` | `devtools/demo_exporter/demo_data_exporter.py` |

直接运行：`python -m devtools.quick_tools.minimal_import_check`

导出演示数据包：`python devcli.py ex` → 默认输出到 `setup/init_data/`（配置见 `devtools/demo_exporter/config.py`）

Data source JobPipeline 样本试跑（从 stock_list 截取 N 只，非全量）::

    python devtools/quick_tools/renew_pipeline_sample.py
    python devtools/quick_tools/renew_pipeline_sample.py --n 120 --source stock_st_periods -v

或手动：`NTQ_DS_SAMPLE_N=80 python cli.py r stock_klines`（默认 80，够测并行+限流）
