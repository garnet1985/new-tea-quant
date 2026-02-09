# Renew Interval 配置方案设计（最终版）

**版本**：3.0  
**最后更新**：2026-01-23

---

## 设计决策

### 最终方案

**只实现 `renew_if_over_days`**：
- 作为默认模式（`renew_mode`）的触发条件
- 简单直接，覆盖常见场景
- 不会带来额外复杂度

**放弃 `renew_interval`（fixed_time_point + action）**：
- 避免过度设计
- 复杂场景通过 `on_before_fetch` 钩子实现
- 保持框架简洁

---

## 配置结构

### 配置结构

```json
{
  "renew_mode": "incremental",
  "renew_if_over_days": {
    "value": 30,                  // 间隔天数（自然日）
    "counting_field": "date"      // 可选，用于检查的日期字段（默认使用 date_field）
  }
}
```

### 字段说明

- `value`: integer，间隔天数（自然日），例如 `30` 表示30天
- `counting_field`: string（可选），用于检查的日期字段名，默认使用 `date_field`。如果数据使用其他字段（如 `event_date`, `last_update`），可以指定

### 设计原则

1. **作为默认模式的触发条件**：
   - `renew_if_over_days` 是 `renew_mode` 的补充参数
   - 不是独立的触发条件，而是对默认模式的细化
   - 只有当距离上次更新时间超过 N 天（自然日）时，才触发更新

2. **简单直接**：
   - 只支持自然日单位，逻辑简单清晰
   - 配置清晰，易于理解

3. **复杂场景通过钩子**：
   - `fixed_time_point` 等复杂场景通过 `on_before_fetch` 钩子实现
   - 保持框架简洁

---

## 配置示例

### 示例1：复权因子事件（至少15天未更新才更新）

```json
{
  "renew_mode": "incremental",
  "renew_if_over_days": {
    "value": 15,
    "counting_field": "last_update"
  }
}
```

### 示例2：切片数据（至少30天未更新才更新）

```json
{
  "renew_mode": "incremental",
  "renew_if_over_days": {
    "value": 30
  }
}
```

### 示例3：K线周线（至少1周未更新才更新）

```json
{
  "renew_mode": "incremental",
  "renew_if_over_days": {
    "value": 7
  }
}
```

### 示例4：不使用 renew_if_over_days（默认行为）

```json
{
  "renew_mode": "incremental"
  // 不使用 renew_if_over_days，每次都会更新
}
```

---

## 工作原理

### renew_if_over_days 模式

1. **查询数据库获取每个 entity 的最新日期**：
   - 按 `counting_field` 字段查询
   - 如果没有 `counting_field`，使用默认 `date_field`

2. **计算当前日期与最新日期的天数差**：
   - 使用自然日计算（不区分交易日）

3. **判断是否需要更新**：
   - 如果天数差 >= `value` 天，则将该 entity 加入更新列表
   - 如果天数差 < `value` 天，则跳过该 entity

4. **使用 renew_mode 的更新策略**：
   - 如果 `renew_mode: "incremental"`，使用增量更新
   - 如果 `renew_mode: "rolling"`，使用滚动更新
   - 如果 `renew_mode: "refresh"`，使用全量刷新

---

## 复杂场景实现（通过钩子）

### fixed_time_point 场景

**需求**：固定时间点更新（如每月第一天、财报季度月份）

**实现方式**：通过 `on_before_fetch` 钩子实现

**示例代码**：
```python
class CorporateFinanceHandler(BaseHandler):
    def on_before_fetch(self, context: Dict[str, Any], apis: List[ApiJob]) -> List[ApiJob]:
        # 检查是否是固定时间点
        current_date = datetime.now()
        is_quarter_month = current_date.month in [1, 4, 7, 10] and current_date.day == 1
        
        if is_quarter_month:
            # 固定时间点：强制更新所有股票
            all_stocks = context.get("stock_list", [])
            # 创建所有股票的 ApiJobs
            # ...
        else:
            # 平时：游标抽样（用户自己实现）
            # ...
        
        return apis
```

---

## 配置验证

### 必填字段
- `value`: 必须提供（间隔天数）

### 字段值验证
- `value`: 必须是正整数
- `counting_field`: 必须是字符串（如果提供）

---

## 与现有配置的兼容性

### 迁移示例

**旧配置（adj_factor_event）**：
```json
{
  "update_threshold_days": 15
}
```

**新配置**：
```json
{
  "renew_mode": "incremental",
  "renew_if_over_days": {
    "value": 15,
    "counting_field": "last_update"
  }
}
```

**旧配置（stock_index_indicator_weight）**：
```json
{
  // 代码中硬编码：至少30天才更新
}
```

**新配置**：
```json
{
  "renew_mode": "incremental",
  "renew_if_over_days": {
    "value": 30
  }
}
```

---

## 实现位置

### 核心逻辑位置

1. **配置读取**：`core/modules/data_source/data_class/config.py`
   - 添加 `get_renew_if_over_days()` 方法

2. **触发检查**：`core/modules/data_source/base_class/base_handler.py`
   - 在 `on_before_fetch` 之后检查 `renew_if_over_days`
   - 过滤不需要更新的 entity

3. **辅助方法**：`core/modules/data_source/service/handler_helper.py`
   - 添加 `check_renew_if_over_days()` 方法
   - 查询数据库、计算天数差、判断是否需要更新

---

## 总结

### 设计原则

1. **简单优先**：只实现核心功能（renew_if_over_days）
2. **灵活扩展**：复杂场景通过钩子实现
3. **清晰语义**：配置意图明确，易于理解

### 实现范围

✅ **实现**：
- `renew_if_over_days` 配置
- 数据库查询和天数差计算
- Entity 过滤逻辑

❌ **不实现**：
- `fixed_time_point` 配置（通过钩子实现）
- `action` 配置（通过钩子实现）
- 多个特殊动作（通过钩子实现）
