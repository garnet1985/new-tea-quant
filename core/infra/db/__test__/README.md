# Database 模块单元测试

## 📁 测试组织方式

采用 `__test__` 文件夹方式，测试代码与源代码放在同一目录下：

```
core/infra/db/
├── db_manager.py
├── db_base_model.py
├── db_schema_manager.py
├── batch_write_queue.py
├── adapters/
│   ├── factory.py
│   └── __test__/
│       └── test_factory.py
└── __test__/
    ├── __init__.py
    ├── test_db_manager.py
    ├── test_db_base_model.py
    ├── test_db_schema_manager.py
    └── test_batch_write_queue.py
```

## 🎯 设计理念

- **就近原则**：测试代码与源代码放在一起，便于维护
- **模块化**：每个模块的测试独立，互不干扰
- **清晰命名**：`__test__` 明确表示测试目录

## 🚀 运行测试

### 运行所有测试

```bash
# 在项目根目录
pytest core/infra/db/__test__/ -v
```

### 运行特定测试文件

```bash
pytest core/infra/db/__test__/test_db_manager.py -v
```

### 运行特定测试类

```bash
pytest core/infra/db/__test__/test_db_manager.py::TestDatabaseManager -v
```

### 运行特定测试方法

```bash
pytest core/infra/db/__test__/test_db_manager.py::TestDatabaseManager::test_init_with_config -v
```

## 📋 测试覆盖

### DatabaseManager 测试
- ✅ `__init__()` - 初始化（有配置/无配置）
- ✅ `set_default()` / `get_default()` - 默认实例管理
- ✅ `reset_default()` - 重置默认实例
- ✅ `initialize()` - 初始化数据库管理器
- ✅ `execute_sync_query()` - 执行同步查询
- ✅ `get_stats()` - 获取统计信息
- ✅ `close()` - 关闭数据库连接

### DbBaseModel 测试
- ✅ `__init__()` - 初始化（有 db/无 db）
- ✅ `load()` - 加载数据
- ✅ `load_one()` - 加载单条数据
- ✅ `save()` - 保存单条数据
- ✅ `save_many()` - 批量保存

### DBService 测试
- ✅ `to_columns_and_values()` - 转换为列名和占位符
- ✅ `to_upsert_params()` - 转换为 upsert 参数

### DbSchemaManager 测试
- ✅ `__init__()` - 初始化
- ✅ `load_schema_from_file()` - 从文件加载 schema
- ✅ `register_table()` - 注册表
- ✅ `get_table_schema()` - 获取表 schema
- ✅ `get_table_fields()` - 获取表字段

### BatchWriteQueue 测试
- ✅ `__init__()` - 初始化
- ✅ `enqueue()` - 入队
- ✅ `flush()` - 刷新队列
- ✅ `get_stats()` - 获取统计信息
- ✅ `shutdown()` - 关闭队列

### DatabaseAdapterFactory 测试
- ✅ `create()` - 创建适配器（PostgreSQL/MySQL/SQLite）
- ✅ `create_from_legacy_config()` - 从旧配置创建适配器

## 🔧 测试框架

使用 **pytest** 作为测试框架：

- **优点**：
  - 简洁的语法
  - 丰富的断言
  - 详细的错误信息
  - 支持 fixtures
  - 自动发现测试

## 📝 编写测试的注意事项

1. **测试类命名**：`Test{ClassName}`
2. **测试方法命名**：`test_{method_name}`
3. **使用断言**：`assert` 语句
4. **测试隔离**：每个测试应该独立，不依赖其他测试
5. **Mock 使用**：使用 `unittest.mock` 模拟外部依赖

## ✅ 当前状态

- ✅ 核心功能测试已覆盖
- ✅ 使用 Mock 避免真实数据库依赖
- ✅ 测试运行时间：< 1 秒
