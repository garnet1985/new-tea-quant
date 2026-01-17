# Userspace Providers

## 📋 概述

用户自定义的 Provider 实现。所有 Provider 都应该放在这里。

## 🏗️ 默认内置 Providers

### TushareProvider

**位置：** `userspace/data_source/providers/tushare/`

**用途：** 用于多个 data source（如 `latest_trading_date`、`kline`、`corporate_finance` 等）

**配置：**
- 创建 `userspace/data_source/providers/tushare/auth_token.txt` 文件，内容为你的 Tushare token（一行）
- 或者设置环境变量 `TUSHARE_TOKEN=your_token`

**文件结构：**
```
userspace/data_source/providers/tushare/
├── __init__.py
├── provider.py          # TushareProvider 实现
├── config.py            # 配置加载逻辑
├── auth_token.txt.example  # 配置示例
└── auth_token.txt       # 用户上传（gitignore）
```

### AKShareProvider

**位置：** `userspace/data_source/providers/akshare/`

**用途：** 用于多个 data source（免费数据源）

**文件结构：**
```
userspace/data_source/providers/akshare/
├── __init__.py
└── provider.py          # AKShareProvider 实现
```

### EastMoneyProvider

**位置：** `userspace/data_source/providers/eastmoney/`

**用途：** 用于获取最近交易日等

**文件结构：**
```
userspace/data_source/providers/eastmoney/
├── __init__.py
├── provider.py          # EastMoneyProvider 实现
└── config.py            # 配置加载逻辑
```

### SinaProvider

**位置：** `userspace/data_source/providers/sina/`

**用途：** 用于获取最近交易日等

**文件结构：**
```
userspace/data_source/providers/sina/
├── __init__.py
└── provider.py          # SinaProvider 实现
```

## 🔧 添加新 Provider

1. 在 `userspace/data_source/providers/` 下创建新的 provider 目录
2. 实现 Provider 类（继承 `BaseProvider`）
3. 创建 `config.py` 用于加载配置
4. ProviderInstancePool 会自动扫描并注册

**示例：**
```python
# userspace/data_source/providers/my_provider/provider.py
from core.modules.data_source.base_provider import BaseProvider

class MyProvider(BaseProvider):
    provider_name = "my_provider"
    requires_auth = False
    
    def _initialize(self):
        # 初始化逻辑
        pass
    
    def get_data(self, **kwargs):
        # API 方法
        pass
```

## 📊 Provider 加载优先级

1. **userspace providers**（优先）- 用户自定义的 Provider
2. **core providers**（后备）- 框架默认的 Provider（如果 userspace 中没有）

如果同一个 `provider_name` 在 userspace 和 core 中都存在，userspace 版本会覆盖 core 版本。

## 🔑 配置加载

Provider 配置从以下位置加载（按优先级）：

1. **userspace 配置**（优先）
   - `userspace/data_source/providers/{provider_name}/config.py`
   - `userspace/data_source/providers/{provider_name}/auth_token.txt`

2. **core 配置**（后备）
   - `core/modules/data_source/providers/{provider_name}/config.py`
   - `core/modules/data_source/providers/{provider_name}/auth_token.txt`
