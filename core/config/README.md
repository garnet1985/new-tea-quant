# 配置目录说明

## 目录结构

```
core/config/              # 统一配置目录
├── database/            # 数据库配置（JSON）
│   ├── db_config.json          # 数据库配置（不提交到 Git）
│   ├── db_config.example.json  # 数据库配置模板
│   └── README.md              # 数据库配置说明
├── system.json         # 系统配置（JSON）
├── worker.json         # Worker 配置（JSON）
├── app_config.json     # 应用配置说明
└── loaders/            # 配置加载器（Python）
    ├── db_conf.py      # 数据库配置加载器
    ├── system_conf.py   # 系统配置加载器
    └── worker_conf.py   # Worker 配置加载器

userspace/config/        # 用户全局配置（JSON，覆盖系统默认）
├── database/           # 用户数据库配置（可选）
│   └── db_config.json  # 用户数据库配置（不提交到 Git）
├── system.json         # 用户系统配置（可选）
└── worker.json         # 用户 Worker 配置（可选）
```

## 配置加载优先级

1. **userspace/config/** - 用户全局配置（最高优先级）
2. **core/config/** - 系统默认配置（基础配置）

配置加载器会自动合并这两个目录的配置，用户配置会覆盖系统默认配置。

## 命名规范

- **目录名**：
  - `config/` - 统一配置目录（包含 JSON 配置文件和 Python 加载器）
  - `loaders/` - 配置加载器代码目录（Python，位于 config/ 下）

- **文件名**：
  - `settings.py` - 策略/模块设置（Python）
  - `config.py` - 模块配置（Python，代码中）
  - `*.json` - 配置文件（JSON，用户可编辑）

## 格式规范

- **JSON**：用户可编辑的配置文件
  - 位置：`core/config/`, `userspace/config/`
  - 用途：数据库配置、应用配置等

- **Python**：配置加载器和代码中的设置
  - 位置：`core/config/loaders/`, `settings.py`, `config.py`
  - 用途：配置加载逻辑、策略设置、模块配置等

## 示例

### 数据库配置

**系统默认配置** (`core/config/database/db_config.json`):
```json
{
  "database_type": "postgresql",
  "postgresql": {
    "host": "localhost",
    "port": 5432
  }
}
```

**用户全局配置** (`userspace/config/database/db_config.json`):
```json
{
  "postgresql": {
    "host": "my-db-server",
    "database": "my_stocks"
  }
}
```

**最终配置**（自动合并）:
```json
{
  "database_type": "postgresql",
  "postgresql": {
    "host": "my-db-server",      # 用户配置覆盖
    "port": 5432,                # 系统默认保留
    "database": "my_stocks"      # 用户配置新增
  }
}
```
