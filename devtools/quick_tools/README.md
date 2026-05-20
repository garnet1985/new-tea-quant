# quick_tools

本地开发脚本（非 `setup/` 安装职责）。入口推荐仓库根目录 **`dev-cli.py`**：

| dev-cli | 脚本 |
|---------|------|
| `-ic` | `minimal_import_check.py` |
| `-cc` | `dev_cache.clear_userspace_ntq_dir` |
| `-cu` | `dev_cache.clear_userspace_simulation_cache` |
| `-p -vX.Y.Z` | `publish_prep.py`（版本元数据、徽章、module_info、pytest） |

直接运行：`python -m devtools.quick_tools.minimal_import_check`
