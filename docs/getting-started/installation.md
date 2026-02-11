# 安装指南

## 环境要求

- **Python**: 3.9+
- **数据库**（三选一）：
  - PostgreSQL 12+（推荐，支持多进程并发读）
  - MySQL 5.7+ / MariaDB 10.3+
  - SQLite 3.26+（开发/测试环境）
- **内存**: 8GB+ RAM (推荐)

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd new-tea-quant
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

详细说明请参考：[虚拟环境使用指南](venv-usage.md)

### 3. 安装依赖

```bash
# 确保虚拟环境已激活
pip install -r requirements.txt

# 如果需要升级 pip
pip install --upgrade pip
```

### 4. 配置数据库

创建 `userspace/config/database/postgresql.json`（或复制示例文件）：

```json
{
    "user": "postgres",
    "password": "your_password"
}
```

其他配置（host、port、database 等）使用系统默认值。

**支持的数据库类型**：
- `postgresql`: PostgreSQL（推荐）
- `mysql`: MySQL/MariaDB
- `sqlite`: SQLite（开发/测试环境）

详细配置说明请参考：[配置指南](configuration.md)

### 5. 初始化数据库

```bash
# 使用 PostgreSQL（推荐）
python3 -c "from core.infra.db import DatabaseManager; db = DatabaseManager(); db.initialize(); print('✅ 数据库初始化完成')"

# 或使用 MySQL
# 或使用 SQLite（自动创建文件）
```

### 6. 验证安装

```bash
# 运行应用
python3 start.py --help
```

如果看到帮助信息，说明安装成功！

## 下一步

- 📖 阅读 [配置指南](configuration.md) 了解详细配置
- 🚀 查看 [快速开始](../../user-guide/examples.md) 运行第一个示例
- 📚 阅读 [策略开发指南](../../user-guide/strategy-development.md) 开始开发

## 常见问题

### 问题 1: 找不到 python 命令

```bash
# 使用 python3
python3 -m venv venv
source venv/bin/activate
```

### 问题 2: pip 安装失败

```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像（可选）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 3: 数据库连接失败

- 检查数据库服务是否启动
- 验证配置文件中的连接信息
- 查看 [配置指南](configuration.md) 中的详细说明

---

**相关文档**：
- [虚拟环境使用指南](venv-usage.md)
- [配置指南](configuration.md)
- [项目主 README](../../README.md)
