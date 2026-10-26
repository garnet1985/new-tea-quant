# Setup — 用户指南

**版本：** `0.1.1`

NTQ 安装流程编排——首次启动时检测环境、创建目录、拷贝产物。  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 首次启动 NTQ 时跑一遍完整的安装流水线：检测环境、建 userspace、装依赖、初始化数据库
- CLI 安装和 UI 向导共用同一份编排，不会出现两头各装一半
- 安装完成后写一份 `.ntq/setup-runtime.json` 作为"装好了"的凭证，下次启动直接跳过

## 配置说明

| 配项 | 在哪配 | 默认值 | 说明 |
|------|--------|--------|------|
| `--userspace` | `install.py` 命令行 | 项目根下 `userspace/` 或沿用 `.ntq/userspace-path.json` | 用户数据目录 |
| `--db` | `install.py` 命令行 | `duckdb` | 数据库类型 |
| `--db-host` / `--db-name` / `--db-user` / `--db-password` | `install.py` 命令行 | 空 | PostgreSQL 连接信息 |
| `USE_CHINA_MIRROR` | 环境变量 | 自动判断 | 强制走/不走国内镜像源 |

## 常见使用方式

### 场景 1：默认安装

1. 在项目根目录跑 `python install.py`
2. 等它一步步检测、建目录、装依赖
3. 看到完成提示就可以启动 NTQ 了

### 场景 2：自定义 userspace 路径

1. 跑 `python install.py --userspace /data/ntq`
2. 路径里有空格或中文时记得加引号：`--userspace "/data/我的 NTQ/userspace"`
3. 装完后 `.ntq/userspace-path.json` 会记住这个路径，下次启动自动用

## 常见坑与注意事项

- **首次启动网络不通导致安装失败：** 装依赖要从 PyPI / npm 拉包，网络断了就会停。检查网络后重跑 `install.py` 即可；国内会自动走中科大镜像，断了会换清华/阿里云。
- **权限不足：** userspace 或数据库目录不可写会安装失败。换一个你有写权限的目录，或先 `chmod` 再装。
- **路径含空格或中文没加引号：** 命令行会把路径切成两半，直接报"路径不存在"。给整个路径加双引号。
- **`--userspace` 不可写时不会污染已有配置：** 装失败了不会写入坏的 `userspace-path.json`，重跑就好。

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
