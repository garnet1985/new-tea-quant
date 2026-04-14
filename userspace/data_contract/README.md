# Data Contract（`userspace/data_contract/`）

这里是 **Data Contract 的用户扩展入口**：你可以扩展一种“已有的数据类型”的取数方式，然后让 strategy/tag 在配置里直接引用它。

您需要先理解几个概念：

- `contract`：契约，就是一种符合某种特定格式和属性的数据。比如 K 线数据、宏观经济数据（可以细分）等。
- `loader`：读取器，定义我声明的这个数据契约如何从数据库提取出来。
- `mapping`：蓝图或者说是装配图，连接 contract 和 loader，定义我声明的数据契约该用哪个读取器去取到实际的数据。

这三者连起来，就是一个新的数据契约。

## 一分钟上手（用已有示例理解）

看 `mapping.py` 里注释掉的示例 `custom_map`，您会看到：

- `data_id` 数据契约的唯一标识符，类似身份证号码
- `scope`：契约范围。我这数据是一堆人用一份（GLOBAL），还是每个人用一个属于自己的（PER_ENTITY）。例如 GDP 是全局的，而 K 线数据是每个股票有自己独有的数据。
- `type`：数据种类，只有时序（TIME_SERIES）和非时序（NON_TIME_SERIES），指这个数据是不是随时间流逝而产生。
- `loader`：我用哪个函数去读取数据（指向一个类）。

---

## 白话版：从 0 创建一个新数据契约

### Step 1）先选一个你要扩展的 `data_id`

当前版本里，`data_id` 需要来自 `DataKey` 枚举（例如 `macro.gdp`、`stock.kline`）。  
也就是说，这里通常是“扩展已有 data_id 的契约配置和 loader”，不是新增任意字符串 key。

### Step 2）在 `mapping.py` 写清楚“这是什么数据”

在 `custom_map` 里新增一项。最少写：

- `scope`
- `type`
- `loader`
- `unique_keys`

如果是时序数据，还需要以下字段：

- `time_axis_field`
- `time_axis_format`

例如：

```python
custom_map = {
    DataKey.MACRO_GDP.value: {
        "scope": ContractScope.GLOBAL,
        "type": ContractType.TIME_SERIES,
        "loader": MacroGdpLoaderCustom,
        "unique_keys": ["quarter"],
        "time_axis_field": "quarter",
        "time_axis_format": "YYYYQ",
        "defaults": {},
    }
}
```

### Step 3）在 `loaders/` 里实现 loader

新增对应 loader 文件，逻辑保持“输入参数清晰、输出字段稳定”。

```python
# userspace/data_contract/loaders/macro_gdp_custom.py
class MacroGdpLoaderCustom(BaseLoader):
    def load(self, params, context=None):
        # 从 params/context 里取参数，再读取数据
        start = params.get("start")
        end = params.get("end")
        dm = DataManager()
        data = dm.get_table("my_table").load(start_date=start, end_date=end)
        return data
```

### Step 4）您的新数据契约马上可以被 strategy 或者 tag 模块使用

拿 strategy 模块举例，您可以在配置里加上

```python
# userspace/strategies/my_strategy/settings.py
settings = {
    "data": {
        # ...
        "extra_required_data_sources": [
            {"data_id": DataKey.MACRO_GDP.value, "params": {}}
        ],
        # ...
    }
}
```
您在这里声明的 `params` 会覆盖定义在 map 里的属性，所以 contract 在使用的时候还有机会修改一些固有属性。

然后在 `strategy_worker.py` 里，`scan_opportunity(...)` 拿到的 `data` 字典中就可以直接读取：

```python
macro_rows = data.get(DataKey.MACRO_GDP.value, [])
```

Tag 的接入模式也类似 strategy。

## 目录结构

```text
userspace/data_contract/
├── __init__.py
├── mapping.py
├── loaders/
│   └── __init__.py
└── USER_GUIDE.md
```

## 更多说明

- 详细字段与排错建议见 [USER_GUIDE.md](USER_GUIDE.md)
- Core 侧接口说明见 [core/modules/data_contract/README.md](../../core/modules/data_contract/README.md)
