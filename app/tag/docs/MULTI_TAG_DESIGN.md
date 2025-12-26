# 多 Tag 设计文档

## 📋 问题

原设计：一个 Calculator 只能打一个 tag
新需求：一个 Calculator 可以打多个 tag（如市值分类：大市值、小市值）

## 🎯 新配置结构

```python
Settings = {
    # 1. Calculator 级别配置（共享逻辑）
    "calculator": {
        "meta": {
            "name": "MARKET_VALUE_BUCKET",  # 业务逻辑名字，不是 tag 名
            "description": "按市值阈值给股票打大小市值标签",
            "is_enabled": True,
        },
        "base_term": "daily",
        "required_terms": [],       # 如果只用日线可以空
        "required_data": ["market_value"],

        "core": {
            "mkv_threshold": 1e10,  # 市值阈值
        },

        "performance": {
            "max_workers": 8,           # 可选，默认自动
            "update_mode": "incremental",   # 可选，内部有默认
            "on_version_change": "refresh", # 可选，内部有默认
        },
    },

    # 2. Tag 级配置（一个 Calculator 下多个 tag）
    "tags": [
        {
            "name": "large_market_value",
            "display_name": "大市值股票",
            "description": "市值大于阈值的股票",
            "version": "1.0",
            "is_enabled": True,

            # 这个 tag 自己特殊的参数（如果有的话）
            "core": {
                "label": "large",  # 举例，可有可无
            },
            # 如果有特殊的 update_mode / on_version_change 也可以在这里 override
            # 否则继承 calculator.performance
        },
        {
            "name": "small_market_value",
            "display_name": "小市值股票",
            "description": "市值小于等于阈值的股票",
            "version": "1.0",
            "is_enabled": True,

            "core": {
                "label": "small",
            },
        },
    ],
}
```

## 🔧 设计要点

### 1. 配置合并规则

- **Calculator 级别**：共享配置（base_term, required_terms, required_data, core, performance）
- **Tag 级别**：每个 tag 的元信息（name, display_name, version, is_enabled）
- **合并规则**：
  - `core`: tag.core 会合并到 calculator.core（tag 的 core 覆盖 calculator 的 core）
  - `performance`: tag.performance 会覆盖 calculator.performance（如果存在）
  - 其他字段：tag 级别优先

### 2. Calculator 接口变更

**方案 1：calculate_tag 接收 tag_config**
```python
def calculate_tag(
    self, 
    entity_id: str,
    entity_type: str,
    as_of_date: str, 
    historical_data: Dict[str, Any],
    tag_config: Dict[str, Any]  # 当前 tag 的配置（已合并）
) -> Optional[Any]:
    """为单个 tag 计算"""
    pass
```

**方案 2：calculate_tags 返回多个 tag**
```python
def calculate_tags(
    self, 
    entity_id: str,
    entity_type: str,
    as_of_date: str, 
    historical_data: Dict[str, Any]
) -> Dict[str, Any]:  # key 是 tag name，value 是 tag value
    """为所有 tag 计算，返回字典"""
    pass
```

**推荐方案 1**：更灵活，每个 tag 可以独立控制是否计算

### 3. 执行流程

```
1. 加载 settings
2. 验证 calculator 配置
3. 验证 tags 配置
4. 对每个启用的 tag：
   a. 合并配置（calculator + tag）
   b. 加载历史数据（共享，只加载一次）
   c. 调用 calculate_tag(entity_id, as_of_date, historical_data, tag_config)
   d. 保存 tag 值
```

## 📐 实现细节

### 配置验证

1. **Calculator 级别验证**：
   - calculator.meta.name: 必需
   - calculator.base_term: 必需
   - calculator.performance: 必需（但子字段可选）

2. **Tag 级别验证**：
   - tags: 必需，至少一个 tag
   - 每个 tag: name, display_name, version, is_enabled 必需

3. **合并后验证**：
   - 每个 tag 的最终配置必须完整

### 配置合并

```python
def merge_tag_config(calculator_config: Dict, tag_config: Dict) -> Dict:
    """合并 calculator 和 tag 配置"""
    merged = calculator_config.copy()
    
    # 合并 core（tag 覆盖 calculator）
    if "core" in tag_config:
        merged_core = calculator_config.get("core", {}).copy()
        merged_core.update(tag_config["core"])
        merged["core"] = merged_core
    
    # 覆盖 performance（如果 tag 有）
    if "performance" in tag_config:
        merged["performance"] = tag_config["performance"]
    
    # 添加 tag 元信息
    merged["tag_meta"] = {
        "name": tag_config["name"],
        "display_name": tag_config["display_name"],
        "version": tag_config["version"],
        "description": tag_config.get("description", ""),
    }
    
    return merged
```
