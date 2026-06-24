# Windows 安装指南

本文档帮助 Windows 用户顺利安装 New Tea Quant 项目。

## ✅ 前置条件

- **Python 3.9+** ([下载](https://www.python.org/downloads/))
- **Git** ([下载](https://git-scm.com/download/win))
- **pip** (随 Python 安装)

## 🚀 快速安装（3 步）

### 步骤 1: 克隆项目

```bash
git clone <your-repo-url>
cd new-tea-quant
```

### 步骤 2: 创建虚拟环境（推荐）

```bash
python -m venv venv
venv\Scripts\activate
```

### 步骤 3: 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **注意**: 我们已优化依赖，移除了需要 C 编译器的包。如果仍遇到编译问题，见下方"备选方案"。

---

## 🔧 常见问题排查

### 问题 1: 找不到 C 编译器 (icl, cl, gcc, ...)

**原因**: 某些旧版本依赖包含需要编译的 C 扩展

**解决方案（按优先级）**:

#### 方法 A: 使用预编译包（推荐）

```bash
pip install --only-binary=:all: -r requirements.txt
```

这会强制只安装预编译的二进制包，跳过需要编译的包。

#### 方法 B: 升级 pip 和 setuptools

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

#### 方法 C: 安装 Visual C++ Build Tools（如果上述方法无效）

1. 下载 [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. 运行安装程序，勾选 **"Desktop development with C++"**
3. 安装完成后**重启电脑**
4. 重新运行 `pip install -r requirements.txt`

---

### 问题 2: lxml 安装失败

**原因**: lxml 可能需要 C 编译器或 libxml2

**解决方案**:

```bash
# 方法 1: 使用预编译版本
pip install lxml==6.1.0 --only-binary lxml

# 方法 2: 如果方法 1 失败，使用 conda
conda install -c conda-forge lxml
```

---

### 问题 3: 某些包下载超时

**原因**: PyPI 镜像源访问慢

**解决方案**: 使用国内镜像源

```bash
# 清华镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或阿里云镜像
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
```

永久配置镜像源：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 🔄 完全卸载与重装

如果遇到无法解决的问题：

```bash
# 1. 删除虚拟环境
rmdir /s venv

# 2. 重新创建
python -m venv venv
venv\Scripts\activate

# 3. 清理 pip 缓存
pip cache purge

# 4. 重新安装
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

---

## 📦 Conda 用户（可选）

如果你习惯使用 Anaconda/Miniconda：

```bash
# 1. 创建环境
conda create -n tea-quant python=3.9
conda activate tea-quant

# 2. 安装核心依赖（conda 会自动处理编译问题）
conda install -c conda-forge pandas numpy lxml requests pymysql psycopg2 duckdb

# 3. 安装剩余依赖
pip install -r requirements.txt
```

**优势**:
- ✅ 自动处理 C 扩展编译
- ✅ 隔离环境更干净
- ✅ 科学计算包兼容性更好

---

## ✅ 验证安装成功

运行测试命令：

```bash
python -m core.modules.tag --list
```

如果看到 Tag 场景列表，说明安装成功！

---

## 🆘 获取帮助

如果以上方法都无法解决你的问题：

1. **查看错误日志**: 将完整错误信息保存到文件
2. **提供系统信息**:
   ```bash
   python --version
   pip --version
   systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
   ```
3. **提交 Issue**: 附带错误日志和系统信息到项目仓库

---

## 📊 依赖说明

| 核心依赖 | 用途 | 是否需要编译 |
|---------|------|-------------|
| `pandas` | 数据分析 | ❌ 有预编译版 |
| `numpy` | 数值计算 | ❌ 有预编译版 |
| `duckdb` | 本地数据库 | ❌ 有预编译版 |
| `pymysql` | MySQL 连接 | ❌ 纯 Python |
| `psycopg2-binary` | PostgreSQL 连接 | ❌ 二进制版 |
| `requests` | HTTP 客户端 | ❌ 纯 Python |
| `akshare` | 腾讯前复权数据源 | ❌ 纯 Python |
| `tushare` | 金融数据源 | ❌ 纯 Python |
| `flask` | Web 框架 | ❌ 纯 Python |

**已移除的问题依赖** (2026-06-24 清理):
- ~~`curl-cffi`~~ → 未使用，且需要 C 编译器
- ~~`cffi`~~ → curl-cffi 的依赖
- ~~`loguru`~~ → 未使用，项目采用标准 logging 模块
- ~~`urllib3<2`~~ → 未直接使用，requests 自动管理内部依赖

---

**最后更新**: 2026-06-24
