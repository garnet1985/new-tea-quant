# Setup 脚本（Quick Start 各步）

在**仓库根目录**执行。与根目录 `install.py`、官网 Quick Start 步骤一一对应。

| 步骤 | 脚本 | 说明 |
|------|------|------|
| 环境 | `python3 setup/sys_req_check/install.py` | 校验 Python ≥ 3.9；能执行到此处即说明已能启动 Python |
| 依赖 | `python3 setup/resolve_dep/install.py` | `pip install -r requirements.txt`；可用 `USE_CHINA_MIRROR=1`（亦可 `bash setup/resolve_dep/install_python_deps.sh`） |
| 数据库配置 | `python3 setup/db_init/db_install.py` | 交互写入 `userspace/config/database/`；或 `--from-examples` 从模板复制 |
| 建表 | `python3 setup/db_init/bootstrap_db.py` | 连接库并建 Base Tables（需先完成上一步） |
| Demo 数据 | `bash setup/run_demo_data.sh` | 等价于 `python3 -m setup.demo_data_handler` |

根目录 **`python install.py`**（无 CLI 参数）：若当前未在虚拟环境中，会自动创建 **`venv/`** 并改用其中的 Python 继续执行（避免依赖装进系统全局；`venv/` 已 gitignore）。跳过自动 venv：`NTQ_SKIP_AUTO_VENV=1`。步骤顺序与是否在 tuple 里禁用见根目录 `install.py` 的 `_INSTALL_STEPS`；可选 Demo 步需 **`INSTALL_DEMO_DATA=1`**，具体仍由 `setup/demo_data_handler/install.py` 处理。
