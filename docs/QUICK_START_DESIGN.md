# Quick Start 与安装设计

本文档是 **Quick Start / 一键安装** 的单一设计源：用户路径、脚本职责、与实现状态对齐；官网教程可据此缩写。

---

## 一、用户视角：干净的 Quick Start 阶梯

目标：**最少概念、顺序固定、每步可单独重跑**。建议对外只宣传下面 **5 步**（官网与根 README 一致）。

| 步骤 | 用户做什么 | 系统达到的状态 |
|------|------------|----------------|
| **0. 前置** | 自备 Python（版本见 `requirements`）、PostgreSQL 或 MySQL、已创建空库 | 环境与权限就绪 |
| **1. 获取代码与虚拟环境** | `git clone`；可选 `python -m venv` + `activate` | 仓库在本地 |
| **2. 安装 Python 依赖** | `python install.py`（或 `pip install -r requirements.txt`） | `requirements` 已安装 |
| **3. 配置数据库** | 编辑 `userspace/config/database/`（见 `ConfigManager.load_database_config` 合并规则） | 应用能连上目标库 |
| **4. 表结构就绪** | 运行**建表/引导**入口（见 §3.3；可为显式命令或首次启动时创建） | 业务表存在或与 Demo 要求一致 |
| **5.（可选）Demo 数据** | 将官网下载的 zip 放入 `userspace/demo_data/`，执行 `python -m setup.demo_data_handler`；或在安装时设置 `INSTALL_DEMO_DATA=1` 后执行根目录 `python install.py` | 数据落在 **带前缀** 的表（默认 `test_*`），不覆盖无前缀生产表 |

**设计原则**

- **不**在 install 里安装 PostgreSQL/MySQL 服务（平台差异大、需管理员权限）。
- **不**在 install 里下载 Demo 大包（版权与体积）；只检查本地文件并导入。
- **幂等**：重复执行「依赖安装」应可跳过或快速完成；Demo 导入有明确确认与非空表策略（见 §5）。
- **单一入口优先**：能用一条命令完成的步骤，在文档里只写一个主入口，其它写「等价方式」。

---

## 二、根目录安装入口：`install.py`

### 2.1 当前实现

- **唯一入口**：`python install.py`（Windows / macOS / Linux，需已安装 Python）。
- 流程：根目录 `install.py` 依次调用 `setup/sys_req_check/install.py` → `setup/resolve_dep/install.py`（pip 安装 `requirements.txt`，可选清华镜像）→（可选）`setup/demo_data_handler/install.py`（内部等价于 `python -m setup.demo_data_handler`）。
- 分步脚本仍见 `setup/README.md`（`db_init/db_install.py`、`db_init/bootstrap_db.py` 等）。
- **可选 Demo**：`INSTALL_DEMO_DATA=1` 后再执行根目录 `python install.py`（根无 CLI 参数）；**仅交互终端**自动跑 Demo，非交互则打印手动命令。

### 2.2 建议后续增量（保持脚本仍「薄」）

按实现成本从低到高排列：

1. **自检**：`python3` 存在且 `>=` 项目最低版本；失败时打印明确错误并退出。
2. **配置向导（可选）**：交互式写入 `userspace/config/database/common.json` 与 `postgresql.json` / `mysql.json`；非交互用环境变量或文档说明手改文件。
3. **表结构引导**：调用统一入口（如 `python -m setup.bootstrap` 或现有 DataManager 建表 API），失败时退出非零并提示日志。
4. **与 Demo 串联**：在 2、3 成功后再询问是否导入 Demo（或仍仅通过环境变量/子命令触发）。

**原则**：根目录 **`install.py`** 只做编排；各步逻辑在 **`setup/<step>/install.py`**，共享辅助见 **`setup/setup.py`**。

---

## 三、数据库配置与建表

### 3.1 配置加载（实现已存在）

合并顺序见 `ConfigManager.load_database_config`：

- `core/default_config/database/common.json`（含 `database_type`）
- `core/default_config/database/{postgresql|mysql|sqlite}.json`
- `userspace/config/database/common.json` 与 `userspace/config/database/{type}.json` 覆盖

Quick Start 文档应告诉用户：**至少改 userspace 下配置**，避免直接改 `core/default_config`。

### 3.2 表结构

- 表定义来自 `core/tables` 与各 Model；`DbBaseModel.create_table` 等可在引导流程中调用。
- **Quick Start 是否要求「显式建表一步」**：若应用首次使用即自动建表，文档可写「连接成功后首次启动会自动建表」；若必须批量预建，则 §一 第 4 步为**必选**并实现对应 CLI。

### 3.3 待收敛的「引导入口」名称（实现时二选一即可）

| 方案 | 说明 |
|------|------|
| **A. `python -m setup.bootstrap`** | 专门负责：测连、批量 `create_table`、打印成功/失败 |
| **B. 复用现有入口** | 若已有 `start.py` / 迁移脚本，Quick Start 只链接该命令 |

设计阶段先在文档中统称 **「建表/引导步骤」**，落地后把最终命令写回本文与 README。

---

## 四、官网 / README 的叙事顺序（与 §一 对齐）

1. 安装 Python（平台分节）。
2. 安装 PG 或 MySQL + 建空库（可附 Docker 示例）。
3. 克隆项目 → 虚拟环境（可选）→ `python install.py`。
4. 配置 `userspace/config/database/`。
5. 运行建表/引导（命令以 §3.3 落地为准）。
6. （可选）放入 `userspace/demo_data/*.zip` → `python3 -m setup.demo_data_handler` 或带 Demo 的 install。
7. **下一步**：Tushare token、跑一条最小策略或数据源示例（链到 `user-guide`）。

---

## 五、Demo 数据（与当前实现对齐）

### 5.1 包与目录

- 用户从官网获取 zip，放入 **`userspace/demo_data/`**（可多文件）。
- **不**随 git 分发；install **不下载** zip。

### 5.2 导入行为（`setup.demo_data_handler`）

- 解压到 `userspace/demo_data/_extract/`（可配置保留）；导入成功后默认删除该目录。
- 数据写入 **带前缀** 的目标表（默认前缀 `test_`），与无前缀业务表隔离；`import_data` 在目标与源不同名时会按源表结构建目标表再 `DELETE` + 插入。
- **确认**：交互式输入大写 `YES`；非交互使用 `--confirm`，若目标表已有数据需 `--yes`。

### 5.3 与旧版文档的差异说明

- 早期设想「仅当所有 Demo 表为空才导入」；当前实现为：**非空表需用户明确确认覆盖**（交互 `YES` / 非交互 `--yes`），更贴合「带前缀的 test 表」场景。

---

## 六、Demo 卸载（后续可做）

- 对「Demo 目标表」列表（与前缀一致）执行 `DELETE` 或 `TRUNCATE`，需确认；不 DROP 表。
- 可与「重置业务数据」脚本区分范围；表名单一来源（配置或常量）。

---

## 七、小结

| 项目 | 结论 |
|------|------|
| Quick Start 对外阶梯 | §一 五步；Demo 为可选最后一步。 |
| `install.py` 当前 | 依赖 + 可选交互式 Demo；不含 DB 安装、不含写配置、不含建表。 |
| 下一步工程化 | 自检 Python → 可选配置向导 → 统一建表引导 → 再考虑与 Demo 一键串联。 |
| Demo | `userspace/demo_data/*.zip` + `python3 -m setup.demo_data_handler`；默认 `test_` 前缀与确认流见 §5。 |

本文档随实现迭代更新；**根 README「快速开始」** 宜保持与 §一、§四 同序，避免多套说法。
