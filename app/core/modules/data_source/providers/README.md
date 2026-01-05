# Provider 模块

## 📋 概述

Provider 模块提供第三方数据源的封装和管理。

## 🏗️ 架构

### ProviderInstancePool（全局单例）

提供全局可访问的 Provider 实例池，支持懒加载和多进程环境。

**使用方式：**

```python
from app.core.modules.data_source.providers import get_provider_pool

# 获取池子
pool = get_provider_pool()

# 获取 Provider 实例（懒加载，自动发现 Provider 类）
tushare = pool.get_provider("tushare")
```

**优势：**
- ✅ Handler 作者不需要知道 Provider 类的具体位置
- ✅ 自动发现机制：第一次使用时自动扫描并注册
- ✅ 懒加载：只有使用时才创建实例
- ✅ 灵活：不要求文件夹名和 provider_name 一致，通过类的 provider_name 属性匹配

### Provider 配置

每个 Provider 都有自己的配置模块（`providers/{provider_name}/config.py`），负责：

1. 从 `auth_token.txt` 读取认证信息（用户上传，gitignore）
2. 从环境变量读取（备选）
3. 提供默认配置

**配置优先级：**
1. `auth_token.txt` 文件（最高优先级）
2. 环境变量
3. 默认配置

### Auth Token 文件

每个 Provider 需要用户上传 `auth_token.txt` 文件：

```text
# providers/tushare/auth_token.txt
your_token_here
```

**注意：**
- `auth_token.txt` 已被 gitignore，不会提交到仓库
- 参考 `auth_token.txt.example` 创建自己的文件
- 文件内容只需要一行 token 字符串，会自动去除首尾空白字符

## 📁 文件结构

```
providers/
├── __init__.py                    # 导出 ProviderInstancePool
├── provider_instance_pool.py      # Provider 实例池（单例）
├── tushare/
│   ├── __init__.py
│   ├── provider.py                # TushareProvider 实现
│   ├── config.py                  # 配置加载逻辑
│   ├── auth_token.txt.example     # 配置示例
│   └── auth_token.txt             # 用户上传（gitignore）
└── akshare/
    └── ...
```

## 🔧 添加新 Provider

1. 创建 Provider 类（继承 `BaseProvider`）
2. 创建配置模块 `config.py`（实现 `get_config()` 函数）
3. 创建 `auth_token.py.example` 示例文件
4. 在 Provider 类中声明限流信息

## 📝 使用示例

### Handler 中使用 Provider

```python
from app.core.modules.data_source.providers import get_provider_pool

class MyHandler(BaseHandler):
    async def fetch(self, context):
        # 从池中获取 Provider 实例（只需知道名称）
        pool = get_provider_pool()
        tushare = pool.get_provider("tushare")  # 自动发现 TushareProvider 类
        
        # 使用 Provider
        data = tushare.get_daily_kline(...)
        return data
```

**注意：**
- 不需要导入 Provider 类
- 只需要知道 Provider 的名称（如 "tushare"）
- 自动发现机制会在第一次使用时扫描并注册 Provider 类

### 多进程环境

每个进程有独立的 Provider 池，这是正常行为。如果池失效，会重新创建实例。

