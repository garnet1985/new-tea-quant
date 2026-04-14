# 数据源（`userspace/data_source/`）

这里是**数据接入的用户空间**：您可以配置“要抓哪些数据”（`mapping.py`），也可以新增/替换“怎么抓”（`handlers/` + `providers/`）。

简单来说，先理解 3 个概念：

- `provider`：谁给您数据（比如 AKShare、Tushare、Sina、EastMoney）。
- `handler`：您怎么抓数据（调用哪个 API、传什么参数、怎么整理成统一格式）。
- `mapping`：这是串联整个数据获取流程的装配图。比如我从谁那里取数据（哪个provider）？取到数据后交给谁处理（对应哪个handler）？等等。我可以随时切换我的数据（甚至是完整数据的一部分）的来源和处理方式，也可以作为备选方案的快速切换开关

## 一分钟上手（用已有数据源“GDP”举例如何获取GDP数据）

注：GDP数据源已经存在Tushare版本的，如果您想直接跑起来，请：

1. 配置 Tushare 的认证 Token（见 `providers/tushare/auth_token.txt.example`）。
2. 打开 `mapping.py`，确认目标数据源 `is_enabled=True`。
3. 在仓库根目录运行：

```bash
python start-cli.py renew
```

---

## 简单理解现在的GDP是怎么配置的：从 0 创建一个新数据源（GDP 示例）

我们用“新增一个 GDP 数据源”来举例，只需要以下简单几步：

### Step 1）先给它一个不重复的名字

给我们的新的数据源起个独一无二的名字（也就是key），比如 `gdp_custom`。  

这个名字是机器用的名字，用来串联步骤，也可以当id用，这个名字会用在：
- `mapping.py` 里（作为配置 key）
- `handlers/` 目录里（作为 handler 模块名）

### Step 2）选择数据供应商 provider

先看 `providers/` 下现有 provider（Tushare / AKShare / EastMoney / Sina）里有没有您要的 GDP 接口。（如果您不想用这些 provider，可以自己按照已经存在的例子新建一个就可以了，在里边定义您要使用的 API 就行。详见[providers/README.md](providers/README.md)）

- **如果有**：直接复用，不用改 provider
- **如果没有**：按 `providers/README.md` 的例子给对应 provider 增加一个新 API 方法

例如：

```python
# userspace/data_source/providers/my_provider/provider.py
class MyProvider(...):
    def get_gdp(self, start_date: str, end_date: str):
        # 调用您的外部接口，然后返回原始结果
        return self.client.fetch_gdp(start_date=start_date, end_date=end_date)
```

然后在 handler 里从上下文里的 `providers` 里取到这个 provider，再调用 `get_gdp(...)` 就可以了。

### Step 3）Handler 里定义“怎么处理数据、怎么入库”

Handler 本身有一个默认的执行步骤（您的类继承的 BaseHandler 里有默认流程）。当您通过 provider 的请求得到数据的时候，handler 会自动通过配置帮您掌管限流，快速获取（多线程），整理数据，然后写入数据库。当然，这里的每一步您都可以重新定义（通过定义一个基类里同名的步骤函数来覆盖）。这样您可以通过使用 handler 的默认处理方式或者自定义的一些流程来完成从 provider 的数据获取到放入数据库前的所有工作。当然 handler 随后也能自动帮您写入数据库。

> 请注意：DataSource（数据源）和您的数据库的某张表是强绑定的，如果您还没有数据表，需要先新建一个  
> - 新建数据表在框架中很简单，声明一个表结构框架会帮助您自动生成数据表  
> - 每次程序重新运行的时候才会重新自动创建表

例如：

```python
# handlers/gdp/handler.py（决定“怎么抓 + 怎么整理”）
class GdpCustomHandler(BaseHandler):
    async def fetch(self, context):
        start_date = "20200101"
        end_date = context.get("latest_trading_date")
        provider = self.context["providers"]["my_provider"]
        raw = provider.get_gdp(start_date=start_date, end_date=end_date)
        return raw

    async def normalize(self, raw_data):
        #这里定义您取到provider的裸数据raw_data后怎么做重组和纠错等等
        processed_data = self._my_logic_to_process_data(raw_data)
        return processed_data
```

### Step 4）在 mapping 里把前面步骤串起来并启用

在 `mapping.py` 的 `DATA_SOURCES` 里增加：

- `handler`: 指向您刚写的 handler
- `depends_on`: 需要的依赖（如 `latest_trading_date`）
- `is_enabled: True`

例如：

```python
# mapping.py（决定“跑哪个数据源”）
DATA_SOURCES = {
    "gdp_custom": {
        "handler": "gdp_custom.GdpCustomHandler",
        "is_enabled": True,
        "depends_on": ["latest_trading_date"],
    }
}
```

完成后，运行：

```bash
python start-cli.py renew
```

这样您的新数据源就会进入统一更新流程，数据会被拉取并写入数据库。

当然，我们的DataSource模块的功能远比这个复杂，详细用法请参考[USER_GUIDE.md](USER_GUIDE.md)

## 目录结构

```text
userspace/data_source/
├── mapping.py              # 选择抓哪些数据、用哪个 handler、依赖关系
├── handlers/               # 各类数据的 handler（怎么抓 + 怎么清洗）
├── providers/              # 外部数据源 provider（Tushare/AKShare/...）
└── USER_GUIDE.md
```
