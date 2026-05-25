# quick_tools

本地开发脚本（非 `setup/` 安装职责）。入口推荐仓库根目录 **`dev-cli.py`**：

| dev-cli | 脚本 |
|---------|------|
| `-ic` | `minimal_import_check.py` |
| `-cc` | `dev_cache.clear_userspace_ntq_dir` |
| `-cu` | `dev_cache.clear_userspace_simulation_cache` |
| `-p -vX.Y.Z` | `publish_prep.py`（版本元数据、徽章、module_info、pytest） |
| `-ex` | `devtools/demo_exporter/demo_data_exporter.py`（分层抽样 → 可导入 zip） |

直接运行：`python -m devtools.quick_tools.minimal_import_check`

导出演示数据包：`python dev-cli.py -ex` → 默认输出到 `setup/init_data/`（配置见 `devtools/demo_exporter/config.py`）
