---
title: 用户空间隔离
aliases:
  - userspace
  - isolation
  - core
  - extension
  - configuration
summary: NTQ userspace与core隔离的设计理念和工作原理。
---

# 用户空间隔离：core 与 userspace

## 设计理念

NTQ 将框架代码和用户代码物理隔离：

- **`core/`** — 框架本体，版本升级时整体替换

- **`userspace/`** — 用户策略、扩展、配置、运行时状态，升级时保留

这保证了用户可以在不修改框架源码的前提下扩展功能，框架升级也不会覆盖用户代码。

## 目录结构

### core/

```
core/
├── bff/                    后端 API 层
├── default_config/        框架默认配置（database/data/system/worker）
├── infra/                  基础设施层
│   ├── cli/                CLI 层
│   ├── db/                 数据库层
│   ├── discovery/          发现层
│   ├── project_context/    路径/配置/发现管理
│   ├── setup/              安装工具
│   ├── updater/            升级器
│   └── utils/              通用工具
├── modules/                框架模块
│   ├── adapter/
│   ├── backtest_engine/
│   ├── data_contract/
│   ├── data_manager/
│   ├── market_profile/
│   ├── strategy/
│   └── tag/
└── tables/                 系统数据表和模型
```

### userspace/

```
userspace/
├── strategies/             用户策略
├── extensions/              框架扩展
│   ├── adapters/           Scanner 后处理适配器
│   ├── tags/               标签场景
│   ├── data_source/        数据源 provider/handler
│   ├── data_contract/      用户数据合约声明
│   ├── assistant/          助手 provider
│   └── tables/             用户自定义表
└── system/                 用户系统配置
    ├── config/             覆盖 core 默认配置
    │   ├── database/       DB 配置覆盖
    │   └── *.json          data/system/worker 配置覆盖
    ├── db/                 用户数据库目录
    ├── backup/             备份目录
    ├── updater/            升级器目录
    └── .ntq/               内部状态/缓存
```

## Userspace 根目录解析

按优先级查找：

1. 环境变量 `NEW_TEA_QUANT_USERSPACE_ROOT`
2. 环境变量 `NTQ_USERSPACE_ROOT`
3. `.ntq/userspace-path.json` 中指定的路径
4. 默认：项目根目录下的 `userspace/`

```python
from core.infra.project_context import PathManager
userspace_root = PathManager.get_userspace_root()
```

## 跨边界导入

框架通过**模块名约定 + 运行时动态导入**定位 userspace 扩展：

| 扩展类型 | 物理路径                                              | 导入路径                                           |
| ---- | ------------------------------------------------- | ---------------------------------------------- |
| 适配器  | `userspace/extensions/adapters/<name>/adapter.py` | `userspace.extensions.adapters.<name>.adapter` |
| 标签   | `userspace/extensions/tags/<path>/`               | 通过 `ProjectContext.path.get_tags_root()` 扫描    |
| 数据合约 | `userspace/extensions/data_contract/<key>/`       | 通过 `ContractIssuer.discover()` 扫描              |
| 数据源  | `userspace/extensions/data_source/providers/`     | 通过发现层扫描                                        |

```python
# AdapterLoader 示例
import importlib

module = importlib.import_module(f"userspace.extensions.adapters.{name}.adapter")
```

框架不需要知道用户扩展的具体路径——只需要遵循命名约定。

## 配置合并

核心配置 + 用户覆盖，环境变量优先级最高：

```
core/default_config/database/*.json  →  userspace/system/config/database/*.json  →  环境变量
core/default_config/{name}.json      →  userspace/system/config/{name}.json
```

```python
from core.infra.project_context import ProjectContext

# 加载数据库配置（自动合并）
db_config = ProjectContext.config.load_database_config("duckdb")

# 加载核心配置（自动合并）
data_config = ProjectContext.config.load_core_config("data")
```

`DiscoveryManager` 实现了统一的发现模式：归一化 domain 和 config\_id，发现 core 和 userspace 的 JSON 路径，通过 `ConfigManager` 合并加载。

## 用户扩展开发

### 新增适配器

```
userspace/extensions/adapters/my_adapter/
├── adapter.py      继承 BaseOpportunityAdapter
└── settings.py     可选配置
```

### 新增标签

```
userspace/extensions/tags/my_tag/
├── tag.py          继承 TagHooks
└── settings.py     标签配置
```

### 新增数据合约

```
userspace/extensions/data_contract/my_data/
├── declaration.py  导出 XXX_DECLARATION
└── loader.py        继承 BaseDataContractLoader
```

同时需要在 userspace 的 `data_keys.py` 中注册 `USER_DATA_KEY`。

## 初始化

userspace 可从 zip 包安装：

1. 读取 `initialization/userspace/userspace.zip`
2. 解压到目标 userspace 目录
3. 处理 zip 内可能的外层 `userspace/` 目录
4. 写入 `.ntq/userspace-path.json`
5. 如果缺少 `system/config/database/common.json`，创建默认 DuckDB 配置

打包脚本会清理运行时内容（`.ntq`、`results/`、缓存、密钥），确保分发包干净。

## 升级

框架升级时：

- `core/` 整体替换为新版本

- `userspace/` 保留不动

- 升级后执行 `sync_userspace_updater` 动作：将 `core/infra/updater/core/orchestrator/` 同步到 `userspace/system/updater/`

- 用户配置和策略不受影响

## 版本追踪

| 维度   | 来源                                            |
| ---- | --------------------------------------------- |
| 框架版本 | `MetaNamespace.core_version()`                |
| 引擎版本 | `get_version()`，记录在策略模拟元数据中                   |
| 策略版本 | `VersionMetaStore` 管理 `simulations/meta.json` |

## 设计边界

| core 负责 | userspace 负责                                  |
| ------- | --------------------------------------------- |
| 框架模块实现  | 策略代码（strategy.py + settings.py）               |
| 默认配置    | 配置覆盖                                          |
| 系统数据表   | 用户自定义表                                        |
| 发现和加载机制 | 扩展实现（adapter/tag/data\_contract/data\_source） |
| 数据库连接管理 | 用户数据库文件                                       |
| CLI 命令  | 无（用户不修改 CLI）                                  |

