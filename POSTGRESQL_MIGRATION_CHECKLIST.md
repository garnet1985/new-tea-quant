# PostgreSQL 迁移清单

## 📋 迁移概览

**目标**：将数据库从 DuckDB 迁移到 PostgreSQL，解决多进程并发读限制问题。

**状态**：✅ **数据迁移已完成**（2026-01-15）

所有数据已成功从 DuckDB 迁移到 PostgreSQL，验证通过。

---

## ✅ 阶段 0：环境准备

### 0.1 验证 PostgreSQL 安装

**状态**：✅ **已安装 PostgreSQL 18.1**

**安装位置**：`/Library/PostgreSQL/18`

**可执行文件路径**：`/Library/PostgreSQL/18/bin/psql`

**服务状态**：✅ **正在运行**

**操作**：
```bash
# 使用完整路径访问 psql（或添加到 PATH）
export PATH="/Library/PostgreSQL/18/bin:$PATH"

# 验证安装
/Library/PostgreSQL/18/bin/psql --version

# 创建数据库和用户
/Library/PostgreSQL/18/bin/createdb -U postgres stocks_py
/Library/PostgreSQL/18/bin/psql -U postgres -d stocks_py -c "CREATE USER stocks_user WITH PASSWORD 'your_password';"
/Library/PostgreSQL/18/bin/psql -U postgres -d stocks_py -c "GRANT ALL PRIVILEGES ON DATABASE stocks_py TO stocks_user;"
```

**验证**：
- [x] PostgreSQL 已安装（PostgreSQL 18.1）
- [x] PostgreSQL 服务正在运行
- [x] 可以连接到数据库
- [x] 已创建 `stocks_py` 数据库
- [x] 已创建 `postgres` 用户（使用 postgres 用户）

**注意**：
- PostgreSQL 需要密码认证，连接时需要提供 postgres 用户密码
- 可以通过 pgAdmin 4 或命令行设置密码
- 建议创建 `.pgpass` 文件存储密码（格式：`hostname:port:database:username:password`）

---

### 0.2 安装 Python PostgreSQL 驱动

**操作**：
```bash
# 安装 psycopg2（PostgreSQL 适配器）
pip install psycopg2-binary

# 或者使用 psycopg3（新版本）
pip install psycopg[binary]
```

**验证**：
- [x] `import psycopg2` 成功
- [x] 可以创建数据库连接

---

## 🏗️ 阶段 1：创建数据库适配器抽象层

### 1.1 创建数据库适配器基类

**文件**：`app/core/infra/db/adapters/base_adapter.py`

**状态**：✅ **已完成**

**任务**：
- [x] 定义 `BaseDatabaseAdapter` 抽象基类
- [x] 定义接口方法：
  - `connect()` - 建立连接
  - `execute_query(query, params)` - 执行查询
  - `execute_write(query, params)` - 执行写入
  - `execute_batch(query, params_list)` - 批量写入
  - `transaction()` - 事务上下文管理器
  - `close()` - 关闭连接
  - `get_connection()` - 获取连接
  - `is_table_exists()` - 检查表是否存在
- [x] 定义占位符转换方法（`%s` vs `?`）

**接口设计**：
```python
from abc import ABC, abstractmethod

class BaseDatabaseAdapter(ABC):
    @abstractmethod
    def connect(self, config: Dict) -> Any:
        """建立数据库连接"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Any = None) -> List[Dict]:
        """执行查询，返回字典列表"""
        pass
    
    @abstractmethod
    def get_placeholder(self) -> str:
        """返回占位符类型：'%s' 或 '?'"""
        pass
```

---

### 1.2 实现 PostgreSQL 适配器

**文件**：`app/core/infra/db/adapters/postgresql_adapter.py`

**状态**：✅ **已完成**

**任务**：
- [x] 实现 `PostgreSQLAdapter` 继承 `BaseDatabaseAdapter`
- [x] 实现连接管理（使用连接池）
- [x] 实现查询执行（返回字典列表）
- [x] 实现占位符转换（`%s` -> `%s`，PostgreSQL 使用 `%s`）
- [x] 实现事务管理
- [x] 实现连接包装器（兼容 DuckDB 接口）

**关键点**：
- PostgreSQL 使用 `%s` 占位符（与 MySQL 相同）
- 需要连接池管理（`psycopg2.pool` 或 `psycopg` 连接池）
- 结果集需要转换为字典格式

---

### 1.3 实现 DuckDB 适配器（保留兼容）

**文件**：`app/core/infra/db/adapters/duckdb_adapter.py`

**状态**：✅ **已完成**

**任务**：
- [x] 实现 `DuckDBAdapter` 继承 `BaseDatabaseAdapter`
- [x] 将现有 `DatabaseManager` 的 DuckDB 逻辑迁移到适配器
- [x] 保持向后兼容（用于双写模式）

**关键点**：
- DuckDB 使用 `?` 占位符
- 单文件数据库，无需连接池
- 保持现有功能不变

---

### 1.4 创建适配器工厂

**文件**：`app/core/infra/db/adapters/factory.py`

**状态**：✅ **已完成**

**任务**：
- [x] 实现 `DatabaseAdapterFactory`
- [x] 根据配置选择适配器（`postgresql` 或 `duckdb`）
- [x] 提供统一的适配器创建接口
- [x] 支持向后兼容（自动检测旧格式配置）

**配置示例**：
```python
{
    "database_type": "postgresql",  # 或 "duckdb"
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "stocks_py",
        "user": "stocks_user",
        "password": "your_password",
        "pool_size": 10
    },
    "duckdb": {
        "db_path": "data/stocks.duckdb",
        "threads": 4,
        "memory_limit": "8GB"
    }
}
```

---

## 🔧 阶段 2：重构 DatabaseManager

### 2.1 修改 DatabaseManager 使用适配器

**文件**：`app/core/infra/db/db_manager.py`

**状态**：✅ **已完成**

**任务**：
- [x] 移除直接的 `duckdb` 导入
- [x] 使用 `DatabaseAdapterFactory` 创建适配器
- [x] 将数据库操作委托给适配器
- [x] 保持现有 API 不变（向后兼容）

**修改点**：
- [x] `__init__()` - 使用适配器工厂，支持旧格式配置自动转换
- [x] `initialize()` - 调用适配器的 `connect()`
- [x] `execute_sync_query()` - 调用适配器的 `execute_query()`
- [x] `transaction()` - 使用适配器的事务管理器
- [x] `get_connection()` - 返回适配器的连接（兼容包装）
- [x] `_direct_write()` - 使用适配器的 `execute_batch()`

---

### 2.2 修改 DuckDBCursor 为通用 Cursor

**文件**：`app/core/infra/db/db_manager.py`

**状态**：✅ **已完成**

**任务**：
- [x] 重命名 `DuckDBCursor` 为 `DatabaseCursor`
- [x] 使其适配不同数据库的游标
- [x] 统一结果集格式（字典列表）

**关键点**：
- PostgreSQL 的 `psycopg2.extras.RealDictCursor` 可以直接返回字典
- DuckDB 需要手动转换
- 适配器统一处理结果格式转换

---

### 2.3 更新配置加载

**文件**：`app/core/conf/db_conf.py`

**状态**：✅ **已完成**

**任务**：
- [x] 新增 `load_db_conf()` 函数（支持统一配置）
- [x] 保留 `load_duckdb_conf()` 函数（向后兼容）
- [x] 支持加载 PostgreSQL 和 DuckDB 配置
- [x] 添加 `database_type` 配置项
- [x] 保持向后兼容（自动检测旧格式配置并转换）

---

## 📐 阶段 3：适配 Schema 管理器

### 3.1 修改 Schema SQL 生成

**文件**：`app/core/infra/db/db_schema_manager.py`

**状态**：✅ **已完成**

**任务**：
- [x] 修改 `_generate_field_definition()` 支持多数据库类型
- [x] 修改 `generate_create_table_sql()` 支持多数据库语法
- [x] 修改 `generate_create_index_sql()` 支持多数据库索引语法
- [x] 添加类型映射：支持 PostgreSQL、MySQL、SQLite

**类型映射**：
- `VARCHAR` -> `VARCHAR`（所有数据库相同）
- `TEXT` -> `TEXT`（PostgreSQL/MySQL/SQLite 都支持）
- `BOOLEAN` -> `BOOLEAN`（PostgreSQL）/ `TINYINT(1)`（MySQL）/ `INTEGER`（SQLite）
- `INTEGER` -> `INTEGER`（所有数据库相同）
- `DATETIME` -> `TIMESTAMP`（PostgreSQL）/ `DATETIME`（MySQL）/ `TEXT`（SQLite）
- `AUTO_INCREMENT` -> `SERIAL`（PostgreSQL）/ `AUTO_INCREMENT`（MySQL）/ `AUTOINCREMENT`（SQLite）

**关键差异**：
- PostgreSQL: 使用 `SERIAL` 或 `GENERATED ALWAYS AS IDENTITY`
- MySQL: 使用 `AUTO_INCREMENT`
- SQLite: 使用 `INTEGER PRIMARY KEY AUTOINCREMENT`
- COMMENT: PostgreSQL 使用 `COMMENT ON COLUMN`，MySQL 在字段定义中，SQLite 不支持

---

### 3.2 修改表存在检查

**文件**：`app/core/infra/db/db_schema_manager.py`

**状态**：✅ **已完成**

**任务**：
- [x] 修改 `is_table_exists()` 支持多数据库的 `information_schema`
- [x] 适配不同的 SQL 语法

**不同数据库的查询**：
- PostgreSQL: `information_schema.tables WHERE table_schema = 'public' AND table_name = %s`
- MySQL: `information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s`
- SQLite: `sqlite_master WHERE type='table' AND name = ?`

---

## 💾 阶段 4：数据迁移

### 4.1 创建数据迁移脚本

**文件**：`tools/migrate_duckdb_to_postgresql.py`

**任务**：
- [ ] 连接 DuckDB 源数据库
- [ ] 连接 PostgreSQL 目标数据库
- [ ] 读取所有表列表
- [ ] 按表迁移数据（批量插入）
- [ ] 验证数据完整性（记录数、数据校验和）
- [ ] 支持断点续传

**迁移策略**：
1. 先创建所有表结构（使用 Schema Manager）
2. 按表批量迁移数据（每批 10000 条）
3. 迁移后验证：
   - 记录数一致
   - 关键字段数据一致
   - 索引已创建

---

### 4.2 执行数据迁移

**状态**：✅ **已完成**

**操作**：
```bash
# 1. 迁移小表
python3 tools/migrate_small_tables_first.py

# 2. 迁移 stock_kline（使用 100 万条批量大小）
python3 tools/migrate_duckdb_to_postgresql.py --tables stock_kline --kline-batch-size 1000000

# 3. 验证迁移结果
python3 tools/verify_migration_data.py
```

**验证项**：
- [x] 所有表的记录数一致（17 个表，17,440,973 条记录）
- [x] 数据验证通过
- [x] 索引已创建
- [x] 主键约束正常

---

## 🧪 阶段 5：测试验证

### 5.1 单元测试

**任务**：
- [ ] 测试 PostgreSQL 适配器连接
- [ ] 测试查询操作
- [ ] 测试写入操作
- [ ] 测试事务管理
- [ ] 测试 Schema 创建

---

### 5.2 集成测试

**任务**：
- [ ] 测试 DataManager 初始化
- [ ] 测试数据读取（K线、股票列表等）
- [ ] 测试数据写入
- [ ] 测试多进程 Worker（验证并发读）

**关键测试**：
```python
# 测试多进程并发读
from app.core.infra.worker import ProcessWorker

def test_multiprocess_read():
    """验证 PostgreSQL 支持多进程并发读"""
    worker = ProcessWorker(max_workers=8)
    # 应该不再出现文件锁冲突
```

---

### 5.3 性能测试

**任务**：
- [ ] 对比 DuckDB vs PostgreSQL 查询性能
- [ ] 测试多进程并发读性能
- [ ] 测试写入性能
- [ ] 记录性能指标

**性能基准**：
- 单表查询（100万条记录）
- JOIN 查询（多表关联）
- 批量写入（10000 条/批）
- 多进程并发读（8 进程）

---

## 🔄 阶段 6：双写模式（可选，用于验证）

### 6.1 实现双写逻辑

**任务**：
- [ ] 修改 `DatabaseManager` 支持同时写入两个数据库
- [ ] 添加配置项 `enable_dual_write: true`
- [ ] 实现错误处理（一个失败不影响另一个）

**使用场景**：
- 验证数据一致性
- 性能对比
- 平滑迁移

---

## 🧹 阶段 7：清理和优化

### 7.1 移除 DuckDB 依赖

**状态**：✅ **已完成**

**任务**：
- [x] 移除 `duckdb` 包依赖（标记为可选）
- [x] 移除 DuckDB 适配器代码
- [x] 更新文档和注释

**说明**：DuckDB 已完全移除，不再支持。如需使用，可以重新添加适配器。

---

### 7.2 更新文档

**状态**：✅ **已完成**

**任务**：
- [x] 更新 `README.md` 数据库配置说明
- [x] 更新 `config/database/db_config.example.json`
- [x] 更新所有涉及数据库的文档
- [x] 添加多数据库配置指南（PostgreSQL/MySQL/SQLite）

---

### 7.3 更新 requirements.txt

**状态**：✅ **已完成**

**任务**：
- [x] 添加 `psycopg2-binary`（PostgreSQL 支持）
- [x] 标记 `duckdb` 为可选依赖（已注释）

---

## 📊 迁移检查清单

### 代码修改检查

- [x] 数据库适配器抽象层已创建
- [x] PostgreSQL/MySQL/SQLite 适配器已实现
- [x] DatabaseManager 已重构为使用适配器
- [x] Schema 管理器已适配多数据库类型
- [x] 配置加载已更新
- [x] 所有数据库操作已迁移

### 数据迁移检查

- [x] 数据迁移脚本已创建（`tools/migrate_duckdb_to_postgresql.py`）
- [x] 所有表已迁移（17 个表，17,440,973 条记录）
- [x] 数据完整性已验证（`tools/verify_migration_data.py`）
- [x] 索引已创建

### 测试检查

- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 多进程并发读测试通过
- [ ] 性能测试完成

### 文档检查

- [x] README 已更新（数据库配置说明）
- [x] 配置示例已更新（`db_config.example.json`）
- [x] 迁移文档已完善（迁移清单和进度）

---

## 🚨 风险点和注意事项

### 1. 数据迁移风险

- **风险**：数据丢失或不一致
- **缓解**：
  - 迁移前完整备份
  - 迁移后数据验证
  - 保留 DuckDB 数据作为备份

### 2. 性能风险

- **风险**：PostgreSQL 性能可能不如 DuckDB
- **缓解**：
  - 性能测试对比
  - 优化 PostgreSQL 配置
  - 添加必要的索引

### 3. 兼容性风险

- **风险**：SQL 语法差异导致功能异常
- **缓解**：
  - 充分测试
  - 保留 DuckDB 适配器作为回退方案

### 4. 部署风险

- **风险**：生产环境需要部署 PostgreSQL 服务
- **缓解**：
  - 使用 Docker 容器化部署
  - 提供详细的部署文档

---

## 📅 预计时间线

- **阶段 0（环境准备）**：1-2 小时
- **阶段 1（适配器抽象层）**：1-2 天
- **阶段 2（重构 DatabaseManager）**：1-2 天
- **阶段 3（适配 Schema 管理器）**：1 天
- **阶段 4（数据迁移）**：1-2 天（取决于数据量）
- **阶段 5（测试验证）**：2-3 天
- **阶段 6（双写模式，可选）**：1 天
- **阶段 7（清理优化）**：1 天

**总计**：约 1-2 周

---

## 🎯 成功标准

1. ✅ PostgreSQL 已安装并运行
2. ✅ 所有数据已成功迁移（2026-01-15 完成）
3. ⏳ 所有测试通过（待后续测试）
4. ⏳ 多进程 Worker 可以正常并发读（待后续测试）
5. ⏳ 性能满足要求（或可接受）（待后续测试）
6. ✅ 文档已更新（2026-01-15 完成）
7. ✅ 代码清理完成（移除 DuckDB，支持 PostgreSQL/MySQL/SQLite）

---

## 📚 参考资源

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [psycopg2 文档](https://www.psycopg.org/docs/)
- [PostgreSQL 性能优化](https://www.postgresql.org/docs/current/performance-tips.html)
