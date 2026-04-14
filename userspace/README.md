# userspace（用户空间）

框架**唯一建议修改/扩展**的业务侧目录：策略、数据源、标签、扫描适配器与本地配置都在这里；升级 `core/` 时尽量不动或只合并约定变更。

## 子目录

| 目录 | 说明 |
|------|------|
| [strategies/](strategies/README.md) | 策略：`settings.py` + `strategy_worker.py`，结果在 `results/`（通常 gitignore） |
| [data_source/](data_source/README.md) | 数据源 mapping、handlers、providers（Tushare / AKShare 等） |
| [data_contract/](data_contract/README.md) | Data Contract userspace 扩展：`mapping.py` + `loaders/` |
| [tags/](tags/README.md) | 标签场景与 `tag_worker.py` |
| [adapters/](adapters/) | 扫描结果输出适配器（如 console） |
| [config/](config/README.md) | **本地**数据库等 JSON 配置（勿提交含密码的文件；用 `*.example.json` 作模板） |

## 与 CLI 的关系

命令行入口为仓库根目录的 `start-cli.py`。在策略的 `settings.py` 里设置 `is_enabled: True` 后，多数命令可不写 `--strategy`（仅当只有一个启用策略时）。

配置字段的完整说明见 [strategies/settings_example.py](strategies/settings_example.py)。
