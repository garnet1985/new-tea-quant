# Setup 脚本（Quick Start 各步）

在**仓库根目录**执行。与 `install.sh`、官网 Quick Start 步骤一一对应。

| 步骤 | 脚本 | 说明 |
|------|------|------|
| 环境 | `python3 setup/sys_req_check/sys_req_check.py` | 校验 Python ≥ 3.9 |
| 依赖 | `bash setup/resolve_dep/install_python_deps.sh` | `pip install -r requirements.txt`；可用 `USE_CHINA_MIRROR=1` |
| 数据库配置 | `python3 setup/db_init/db_install.py` | 交互写入 `userspace/config/database/`；或 `--from-examples` 从模板复制 |
| 建表 | `python3 setup/db_init/bootstrap_db.py` | 连接库并建 Base Tables（需先完成上一步） |
| Demo 数据 | `bash setup/run_demo_data.sh` | 等价于 `python3 -m setup.demo_data_handler` |

根目录 `./install.sh` 会调用：`sys_req_check` → `resolve_dep/install_python_deps.sh` →（可选）`run_demo_data.sh`。
