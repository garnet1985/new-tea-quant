# 标签系统指南

本指南介绍如何使用和开发标签系统。

## 快速开始

### 使用现有标签场景

```bash
# 计算所有标签场景
python start.py tag

# 计算指定场景
python start.py tag --scenario momentum
```

### 在策略中使用标签

```python
from core.modules.data_manager import DataManager

data_manager = DataManager()
data_manager.initialize()

# 获取标签值
tag_value = data_manager.stock.tags.get_tag_value(
    stock_id="000001.SZ",
    tag_name="momentum_score",
    date="20240101"
)
```

## 开发标签场景

### 1. 创建标签场景目录

```bash
mkdir -p userspace/tags/my_scenario
cd userspace/tags/my_scenario
```

### 2. 创建 Tag Worker

创建 `tag_worker.py`，继承 `BaseTagWorker`：

```python
from core.modules.tag.base_tag_worker import BaseTagWorker

class MyTagWorker(BaseTagWorker):
    """我的标签场景"""
    
    def calculate_tag(self, stock_id: str, date: str) -> dict:
        """计算标签值"""
        # 实现标签计算逻辑
        return {
            "my_tag": value
        }
```

### 3. 创建配置

创建 `settings.py`：

```python
settings = {
    "scenario": {
        "name": "my_scenario",
        "entity_type": "stock",
        "update_mode": "incremental",
    },
    "tags": [],
}
```

### 4. 运行标签计算

```bash
python start.py tag --scenario my_scenario
```

## 详细文档

- [Tag 系统架构](../docs/architecture/tag_architecture.md) - 深入了解标签系统设计
- [Tag README](../../core/modules/tag/README.md) - 标签模块详细文档
- [示例场景](../../userspace/tags/momentum/) - 完整示例代码

## 相关文档

- [策略开发指南](strategy-development.md) - 策略中使用标签
- [数据源使用指南](data-source-usage.md) - 获取基础数据
- [架构文档](../docs/architecture/) - 系统架构文档
