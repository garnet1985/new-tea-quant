# Config 和 Conf 目录分析

## 目录结构

### 1. `config/` (项目根目录)
**用途**：配置文件存储位置（JSON 格式，用户可编辑）

**内容**：
- `database/` - 数据库配置文件目录
  - `db_config.json` - 实际数据库配置（不提交到 Git）
  - `db_config.example.json` - 配置文件模板
  - `pg_config.json` - PostgreSQL 迁移配置
  - `README.md` - 配置说明文档

**特点**：
- JSON 格式，用户可直接编辑
- 包含敏感信息（密码等），不提交到 Git
- 由 `core/conf/db_conf.py` 加载

### 2. `core/conf/` (core 模块下)
**用途**：配置加载代码和系统常量（Python 代码）

**内容**：
- `conf.py` - 系统配置常量
  - `data_default_start_date` - 默认数据开始日期
  - `kline_terms` - K线周期列表
  - `stock_index_indicators` - 股票指数配置字典
- `db_conf.py` - 数据库配置加载模块
  - 从 `config/database/` 读取 JSON 配置文件
  - 支持 PostgreSQL、MySQL、SQLite
  - 包含格式转换逻辑（向后兼容）
- `db.py` - **可能已废弃**
  - 旧的数据库配置（Python 字典格式）
  - 需要检查是否还在使用

## 功能差异

| 特性 | `config/` | `core/conf/` |
|------|-----------|-------------|
| 格式 | JSON | Python |
| 用途 | 存储用户配置 | 配置加载逻辑 + 系统常量 |
| 可编辑性 | 用户可直接编辑 | 代码，需重新部署 |
| 版本控制 | 部分文件不提交 | 全部提交 |
| 位置 | 项目根目录 | core 模块下 |

## 结论

**这两个目录功能不同，不应该合并**：

1. **`config/`** 是配置文件的存储位置（数据层）
   - 用户可编辑的配置文件
   - 包含敏感信息

2. **`core/conf/`** 是配置加载代码和系统常量（代码层）
   - 配置加载逻辑
   - 系统级常量定义

## 待办事项

- [ ] 检查 `core/conf/db.py` 是否还在使用
  - 如果未使用，标记为废弃或删除
  - 如果仍在使用，评估是否可以迁移到 `db_conf.py`
