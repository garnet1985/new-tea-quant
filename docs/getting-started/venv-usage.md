# 虚拟环境使用指南

## 🚀 快速开始

### 1. 创建虚拟环境

```bash
# 进入项目目录
cd /Users/garnet/Desktop/new-tea-quant

# 创建虚拟环境（如果还没有）
python3 -m venv venv
```

### 2. 激活虚拟环境

**macOS / Linux**:
```bash
source venv/bin/activate
```

**Windows**:
```bash
venv\Scripts\activate
```

激活成功后，命令行提示符前会显示 `(venv)`。

### 3. 安装依赖

```bash
# 确保虚拟环境已激活
pip install -r requirements.txt

# 如果需要升级 pip
pip install --upgrade pip
```

### 4. 运行迁移脚本

```bash
# 确保虚拟环境已激活（命令行前有 (venv)）
python tools/migrate_mysql_to_duckdb.py --batch-size 100000
```

---

## 📋 常用命令

### 激活虚拟环境
```bash
source venv/bin/activate  # macOS/Linux
```

### 退出虚拟环境
```bash
deactivate
```

### 检查虚拟环境是否激活
```bash
which python  # 应该显示 venv/bin/python
python --version  # 显示 Python 版本
```

### 查看已安装的包
```bash
pip list
```

### 安装新包
```bash
pip install package_name
```

### 更新 requirements.txt
```bash
pip freeze > requirements.txt
```

---

## 🔧 运行项目命令（在虚拟环境中）

### 运行迁移脚本
```bash
# 基本用法
python tools/migrate_mysql_to_duckdb.py

# 指定批量大小
python tools/migrate_mysql_to_duckdb.py --batch-size 100000

# 迁移特定表
python tools/migrate_mysql_to_duckdb.py --table stock_kline

# 断点续传
python tools/migrate_mysql_to_duckdb.py --resume
```

### 运行主程序
```bash
python start.py --help
```

### 运行安装脚本
```bash
./install.sh
```

---

## ⚠️ 常见问题

### 问题 1: 找不到 python 命令
```bash
# 使用 python3
python3 -m venv venv
source venv/bin/activate
```

### 问题 2: pip 版本过旧
```bash
# 在虚拟环境中升级 pip
pip install --upgrade pip
```

### 问题 3: 权限错误
```bash
# 确保虚拟环境目录有执行权限
chmod +x venv/bin/activate
```

### 问题 4: 虚拟环境已损坏
```bash
# 删除并重新创建
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 💡 最佳实践

1. **每次使用前激活虚拟环境**
   ```bash
   source venv/bin/activate
   ```

2. **在虚拟环境中安装所有依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **不要提交虚拟环境到 Git**
   - `.gitignore` 已包含 `venv/` 和 `.venv/`

4. **使用 requirements.txt 管理依赖**
   ```bash
   # 安装依赖
   pip install -r requirements.txt
   
   # 更新依赖列表
   pip freeze > requirements.txt
   ```

---

## 📝 完整示例

```bash
# 1. 进入项目目录
cd /Users/garnet/Desktop/new-tea-quant

# 2. 创建虚拟环境（如果还没有）
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 升级 pip（可选）
pip install --upgrade pip

# 5. 安装依赖
pip install -r requirements.txt

# 6. 运行迁移脚本
python tools/migrate_mysql_to_duckdb.py --batch-size 100000

# 7. 完成后退出虚拟环境（可选）
deactivate
```

---

## 🔍 验证虚拟环境

运行以下命令验证虚拟环境是否正确设置：

```bash
# 检查 Python 路径
which python
# 应该显示: /Users/garnet/Desktop/new-tea-quant/venv/bin/python

# 检查 pip 路径
which pip
# 应该显示: /Users/garnet/Desktop/new-tea-quant/venv/bin/pip

# 检查已安装的包
pip list | grep duckdb
# 应该显示 duckdb 包
```
