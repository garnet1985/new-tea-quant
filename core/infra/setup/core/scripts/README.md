# core/infra/setup/core/scripts

安装产物工厂（不是安装步骤本身；步骤仍在 `core/infra/setup/core/steps/`）。

| 文件夹 | 入口 | 产出 |
|--------|------|------|
| `init_userspace/` | `devcli.py pu` | `initialization/userspace/userspace.zip` |
| `init_data/` | `devcli.py ex --demo\|--member\|--full` | `userspace/.ntq/packages/{demo\|member\|full}/data_*.zip` |

独立运行仍可用 ``python -m core.infra.setup.core.scripts.init_data``；产品代码请走 ``Setup.artifacts``。
