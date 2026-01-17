# 快速开始指南

手把手创建一个自定义 handler 的完整教程。

---

## 步骤 1：创建 Handler 文件

在 `custom/handlers/` 目录下创建 `my_stock_list.py`：

```python
# custom/handlers/my_stock_list.py
from typing import Dict, Any, List
from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
from core.modules.data_source.data_classes import ApiJob, DataSourceTask
from app.core.modules.data_source.providers import get_provider_pool


class MyStockListHandler(BaseDataSourceHandler):
    """我的自定义股票列表 Handler"""
    
    # 必需：定义类属性
    data_source = "stock_list"
    description = "从 Tushare 获取股票列表"
    
    def __init__(self, schema, params: Dict[str, Any] = None, data_manager=None):
        super().__init__(schema, params, data_manager)
        # 获取 Provider 实例
        pool = get_provider_pool()
        self.tushare = pool.get_provider("tushare")
    
    async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
        """生成 Tasks"""
        task = DataSourceTask(
            task_id="stock_list_all",
            description="获取所有股票列表",
            api_jobs=[
                ApiJob(
                    provider_name="tushare",
                    method="get_stock_list",
                    params={},
                    depends_on=[],
                )
            ],
        )
        return [task]
    
    async def normalize(self, raw_data: Dict) -> Dict:
        """标准化数据"""
        # raw_data 结构：{task_id: {job_id: result}}
        task_id = "stock_list_all"
        job_results = raw_data.get(task_id, {})
        result = list(job_results.values())[0] if job_results else []
        
        # 标准化为 schema 格式
        normalized = []
        for item in result:
            normalized.append({
                "ts_code": item["ts_code"],
                "symbol": item["symbol"],
                "name": item["name"],
                "list_date": item.get("list_date", ""),
            })
        
        return {"data": normalized}
    
    async def after_normalize(self, normalized_data: Dict):
        """保存数据到数据库"""
        if not normalized_data.get("data"):
            return
        
        model = self.data_manager.get_model("stock_list")
        model.replace(normalized_data["data"])
        self.logger.info(f"✅ 保存了 {len(normalized_data['data'])} 条数据")
```

---

## 步骤 2：配置 Handler

在 `custom/mapping.json` 中添加配置：

```json
{
  "data_sources": {
    "stock_list": {
      "handler": "custom.handlers.my_stock_list.MyStockListHandler",
      "is_enabled": true,
      "dependencies": {
        "latest_completed_trading_date": false,
        "stock_list": false
      },
      "params": {}
    }
  }
}
```

---

## 步骤 3：运行

```python
from app.core.modules.data_source.data_source_manager import DataSourceManager

manager = DataSourceManager(is_verbose=False)
await manager.renew_data()
```

---

## 常见场景

### 场景 1：需要依赖数据（如股票列表）

在 `mapping.json` 中声明依赖：

```json
{
  "dependencies": {
    "latest_completed_trading_date": true,
    "stock_list": true
  }
}
```

在 `fetch` 方法中使用：

```python
async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
    stock_list = context.get("stock_list")
    latest_date = context.get("latest_completed_trading_date")
    
    tasks = []
    for stock in stock_list:
        task = DataSourceTask(
            task_id=f"kline_{stock['ts_code']}",
            api_jobs=[
                ApiJob(
                    provider_name="tushare",
                    method="get_daily_kline",
                    params={
                        "ts_code": stock["ts_code"],
                        "end_date": latest_date,
                    },
                    depends_on=[],
                )
            ],
        )
        tasks.append(task)
    return tasks
```

### 场景 2：多个 ApiJob 有依赖关系

```python
async def fetch(self, context: Dict[str, Any]) -> List[DataSourceTask]:
    kline_job = ApiJob(
        provider_name="tushare",
        method="get_daily_kline",
        params={"ts_code": "000001.SZ", "start_date": "20240101"},
        job_id="kline_000001",  # 手动指定 job_id
        depends_on=[],
    )
    
    basic_job = ApiJob(
        provider_name="tushare",
        method="get_daily_basic",
        params={"ts_code": "000001.SZ", "start_date": "20240101"},
        job_id="basic_000001",
        depends_on=["kline_000001"],  # 依赖 kline_job
    )
    
    task = DataSourceTask(
        task_id="task_000001",
        api_jobs=[kline_job, basic_job],
    )
    return [task]
```

---

## 测试单个 Handler

```python
from app.core.modules.data_source.data_source_manager import DataSourceManager

manager = DataSourceManager()
result = await manager.fetch("stock_list", context={})
print(result)
```

---

**更多信息：** 查看 [README.md](./README.md) 了解概念和详细用法。
