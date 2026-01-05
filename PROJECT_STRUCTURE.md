# 项目文件夹结构

```
stocks-py/
├── app/                          # 应用代码
│   ├── core/                     # 核心框架代码（框架层）
│   │   ├── conf/                 # 核心配置
│   │   │   ├── conf.py
│   │   │   └── db.py
│   │   ├── modules/              # 核心业务模块
│   │   │   ├── analyzer/         # 策略分析器
│   │   │   │   ├── components/   # 组件
│   │   │   │   │   ├── entity/   # 实体（投资、机会、目标）
│   │   │   │   │   ├── investment/  # 投资记录
│   │   │   │   │   ├── simulator/   # 模拟器
│   │   │   │   │   └── ...
│   │   │   │   └── strategy/     # 策略实现
│   │   │   │       ├── example/  # 示例策略
│   │   │   │       ├── RTB/      # 反转趋势策略
│   │   │   │       ├── Momentum/ # 动量策略
│   │   │   │       └── ...
│   │   │   ├── data_manager/     # 数据管理器
│   │   │   │   ├── base_tables/  # 基础表模型
│   │   │   │   │   ├── stock_kline/    # K线数据
│   │   │   │   │   ├── stock_list/     # 股票列表
│   │   │   │   │   ├── tag_definition/  # 标签定义
│   │   │   │   │   ├── tag_scenario/    # 标签场景
│   │   │   │   │   ├── tag_value/       # 标签值
│   │   │   │   │   └── ...
│   │   │   │   ├── data_services/  # 数据服务
│   │   │   │   │   ├── stock_related/   # 股票相关
│   │   │   │   │   ├── macro_system/    # 宏观系统
│   │   │   │   │   ├── tag/             # 标签服务
│   │   │   │   │   └── ui_transit/      # UI中转
│   │   │   │   └── helpers/         # 辅助工具
│   │   │   ├── data_source/        # 数据源管理
│   │   │   │   ├── defaults/       # 默认处理器
│   │   │   │   │   └── handlers/   # 数据处理器
│   │   │   │   │       ├── kline/  # K线处理器
│   │   │   │   │       ├── stock_list/  # 股票列表处理器
│   │   │   │   │       └── ...
│   │   │   │   ├── custom/         # 自定义配置
│   │   │   │   └── providers/     # 数据提供方
│   │   │   │       ├── tushare/    # Tushare
│   │   │   │       ├── akshare/    # AKShare
│   │   │   │       └── eastmoney/  # 东方财富
│   │   │   └── tag/                # 标签系统
│   │   │       ├── core/          # 核心功能
│   │   │       │   ├── base_tag_worker.py    # 标签工作器基类
│   │   │       │   ├── tag_manager.py        # 标签管理器
│   │   │       │   ├── components/           # 组件
│   │   │       │   │   ├── helper/           # 辅助工具
│   │   │       │   │   └── tag_worker_helper/  # 工作器辅助
│   │   │       │   ├── models/               # 数据模型
│   │   │       │   │   ├── scenario_model.py # 场景模型
│   │   │       │   │   └── tag_model.py      # 标签模型
│   │   │       │   └── config.py            # 配置
│   │   │       ├── scenarios/      # 标签场景
│   │   │       │   ├── example_settings.py  # 示例配置
│   │   │       │   └── momentum/   # 动量场景示例
│   │   │       └── docs/           # 文档
│   │   ├── global_enums/          # 全局枚举定义
│   │   │   └── enums.py
│   │   ├── infra/                 # 基础设施
│   │   │   ├── db/                # 数据库基础设施
│   │   │   │   ├── db_manager.py      # 数据库管理器
│   │   │   │   ├── db_base_model.py   # 基础模型
│   │   │   │   ├── db_config_manager.py  # 配置管理
│   │   │   │   └── db_schema_manager.py  # Schema管理
│   │   │   └── worker/            # 工作器基础设施
│   │   │       ├── multi_process/ # 多进程
│   │   │       └── multi_thread/  # 多线程
│   │   └── utils/                 # 核心工具库
│   │       ├── date/              # 日期工具
│   │       ├── file/              # 文件工具
│   │       ├── icon/              # 图标服务
│   │       └── progress/           # 进度跟踪
│   └── userspace/                 # 用户空间（用户自定义代码）
│       ├── conf.py                # 用户配置
│       ├── db_conf.py             # 用户数据库配置
│       ├── strategies/            # 用户自定义策略
│       │   ├── mean_reversion/    # 均值回归策略
│       │   ├── momentum/          # 动量策略
│       │   └── random/            # 随机策略
│       ├── data_source/           # 用户自定义数据源
│       └── tags/                  # 用户自定义标签场景
│
├── bff/                          # 后端API服务
│   ├── APIs/                     # API接口
│   ├── app.py
│   └── routes.py
│
├── config/                       # 配置文件
│   ├── app_config.json
│   └── database/                 # 数据库配置
│       ├── db_config.json
│       └── db_config.example.json
│
├── fed/                          # 前端代码
│   ├── src/
│   │   ├── components/          # React组件
│   │   ├── pages/               # 页面
│   │   └── services/           # API服务
│   └── public/
│
├── utils/                        # 根工具库（通用工具）
│   ├── util.py                  # 通用工具函数
│   └── warning_suppressor.py   # 警告抑制器
│
├── tools/                        # 工具脚本
│   ├── compare_qfq_quarterly.py
│   └── ...
│
├── start.py                      # 主入口文件
├── start_bff.py                  # BFF服务入口
├── requirements.txt              # Python依赖
└── README.md                     # 项目说明
```

## 目录结构说明

### 核心架构分层

项目采用**核心框架层**和**用户空间层**的分离架构：

#### 1. **app/core/** - 核心框架层
框架提供的核心功能，用户不应修改：

- **modules/** - 核心业务模块
  - `analyzer/` - 策略分析器框架
  - `data_manager/` - 数据管理器框架
  - `data_source/` - 数据源管理框架
  - `tag/` - 标签系统框架

- **infra/** - 基础设施
  - `db/` - 数据库基础设施（已从 utils 迁移）
  - `worker/` - 工作器基础设施（已从 utils 迁移）

- **utils/** - 核心工具库（已从根目录迁移）
  - `date/` - 日期工具
  - `file/` - 文件工具
  - `icon/` - 图标服务
  - `progress/` - 进度跟踪

- **conf/** - 核心配置
- **global_enums/** - 全局枚举定义

#### 2. **app/userspace/** - 用户空间层
用户自定义代码，可以自由扩展：

- `strategies/` - 用户自定义策略
- `data_source/` - 用户自定义数据源处理器
- `tags/` - 用户自定义标签场景
- `conf.py` - 用户配置
- `db_conf.py` - 用户数据库配置

#### 3. **utils/** - 根工具库
保留在根目录的通用工具，不依赖框架：

- `util.py` - 通用工具函数
- `warning_suppressor.py` - 警告抑制器

## 核心模块说明

### 1. **app/core/modules/analyzer** - 策略分析器
- 负责策略的扫描、模拟、分析
- 包含策略组件和策略实现
- 用户策略放在 `app/userspace/strategies/`

### 2. **app/core/modules/data_manager** - 数据管理器
- 统一的数据访问层
- 管理所有基础表和数据服务
- 提供数据访问API

### 3. **app/core/modules/data_source** - 数据源管理
- 管理外部数据源的获取
- 支持多种数据提供方（Tushare、AKShare等）
- 配置驱动的数据更新流程
- 用户自定义处理器放在 `app/userspace/data_source/`

### 4. **app/core/modules/tag** - 标签系统
- 标签计算和存储框架
- 支持自定义标签场景
- 多进程并行计算
- 用户自定义场景放在 `app/userspace/tags/`

### 5. **app/core/infra/** - 基础设施
- 数据库管理、模型、配置等基础设施
- 多进程/多线程工作器
- 框架层的基础能力

## 架构设计原则

1. **核心与用户分离**：框架代码在 `core/`，用户代码在 `userspace/`
2. **基础设施集中**：数据库、工作器等基础设施统一在 `infra/`
3. **工具库分层**：核心工具在 `core/utils/`，通用工具在根 `utils/`
4. **可扩展性**：用户可以在 `userspace/` 中自由扩展策略、数据源、标签等
