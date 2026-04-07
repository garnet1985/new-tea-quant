# Setup 脚本（Quick Start 各步）

在**仓库根目录**执行。与根目录 `install.py`、官网 Quick Start 步骤一一对应。

| 步骤 | 脚本 | 说明 |
|------|------|------|
| 环境 | `python3 setup/sys_req_check/install.py` | 校验 Python ≥ 3.9；能执行到此处即说明已能启动 Python |
| 依赖 | `python3 setup/resolve_deps/install.py` | `pip install -r requirements.txt`；可用 `USE_CHINA_MIRROR=1` |
| 数据库配置/探活 | `python3 setup/init_database/install.py` | 校验并提示创建 `userspace/config/database/*`；必要时自动创建 DB（PostgreSQL） |
| 初始化数据 | `python3 setup/setup_data/install.py` | 必跑步骤；读取 `setup/init_data/*.zip`，空目录时给出提示并结束 |

根目录 **`python install.py`**（无 CLI 参数）：若当前未在虚拟环境中，会自动创建 **`venv/`** 并改用其中的 Python 继续执行（避免依赖装进系统全局；`venv/` 已 gitignore）。跳过自动 venv：`NTQ_SKIP_AUTO_VENV=1`。步骤顺序与开关见根目录 `install.py` 的 `INSTALL_STEPS`。其中 `setup_data` 为必跑步骤：有数据则导入，无数据则明确提示如何补齐后重跑。
