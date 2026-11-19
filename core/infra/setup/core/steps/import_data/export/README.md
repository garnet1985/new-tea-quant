# import_data / export

演示 / 会员 / 全量数据包导出工厂（原 `core/scripts/init_data`）。

| 入口 | 产出 |
|------|------|
| `devcli.py ex --demo\|--member\|--full` | `userspace/.ntq/packages/{demo\|member\|full}/data_*.zip` |
| `Setup.artifacts.export_demo_data` | 同上 |

独立运行：`python -m core.infra.setup.core.steps.import_data.export --help`。产品代码请走 `Setup.artifacts`。
