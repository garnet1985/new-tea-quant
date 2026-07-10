# Market Profile 架构设计

## 设计理念

采用 **基类 + 继承 + Proxy** 模式，子类只需提供settings，基类提供所有默认实现。

### 核心组件

```
┌─────────────────────────────────────┐
│   MarketRulesProxy（对外暴露）        │
│   - mount(): 挂载当前市场            │
│   - current: 当前市场规则实例         │
│   - get_market(): 获取特定市场       │
│   - list_available(): 列出所有市场   │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│   MarketBaseRules（基类）             │
│   - 配置验证和默认值应用              │
│   - 所有方法的默认实现                │
│   - 从 settings 自动初始化            │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│   SpecificRules（子类）               │
│   - 只需提供 profile_id 和 settings  │
│   - 可选覆盖特殊方法                  │
│   - 代码量极小（约30行）              │
└─────────────────────────────────────┘
```

## Settings 配置结构

```python
settings = {
    "key": "market_id",
    
    "meta": {
        "name": "市场名称",
        "description": "市场描述",
    },
    
    "settlement": {
        "t_plus": 0  # T+N交收周期
    },
    
    "amplitude_limit": {
        "default_ratio": 0.1,  # 默认涨跌幅
        "price_round_decimals": 2,  # 价格小数位数
        "default_risk": {...},  # 风险标签涨跌幅（可选）
        "rules": [...]  # 多规则匹配（可选）
    },
    
    "lot_size": {
        "default_min_lot": 100,  # 默认最小买入单位
        "default_lot_step": 100,  # 默认每手步长
        "rules": [...]  # 多规则匹配（可选）
    }
}
```

## 配置验证和默认值

基类提供 `_validate_and_apply_defaults()` 方法：

```python
def _validate_and_apply_defaults(self, raw_settings):
    """验证配置并应用默认值"""
    validated = {}
    
    # 默认值：
    # - t_plus: 0 (T+0)
    # - default_ratio: 0.0 (无涨跌幅限制)
    # - default_min_lot: 1 (1股起)
    # - default_lot_step: 1 (步长1)
    
    validated["settlement"] = {
        "t_plus": int(settlement.get("t_plus", 0)),
    }
    
    validated["amplitude_limit"] = {
        "default_ratio": float(amplitude.get("default_ratio", 0.0)),
        "price_round_decimals": int(amplitude.get("price_round_decimals", 2)),
        "default_risk": amplitude.get("default_risk", {}),
        "rules": amplitude.get("rules", []),
    }
    
    validated["lot_size"] = {
        "default_min_lot": int(lot_size.get("default_min_lot", 1)),
        "default_lot_step": int(lot_size.get("default_lot_step", 1)),
        "rules": lot_size.get("rules", []),
    }
    
    return validated
```

## 子类实现模式

### 简单市场（无需覆盖）

```python
class ChinaAStockRules(MarketBaseRules):
    @property
    def profile_id(self) -> str:
        return "china_a_stock"
    
    @property
    def settings(self) -> Dict[str, Any]:
        from .settings import settings
        return settings
    
    # A股规则与基类默认实现一致，无需覆盖
```

### 特殊市场（需要覆盖）

```python
class HongKongRules(MarketBaseRules):
    @property
    def profile_id(self) -> str:
        return "hong_kong"
    
    @property
    def settings(self) -> Dict[str, Any]:
        from .settings import settings
        return settings
    
    # 港股特殊：无涨跌幅限制
    def is_within_price_limit(self, current_price, prev_close):
        return True
```

## 设计优势

### 1. 代码量大幅减少

| 市场 | 重构前 | 重构后 | 减少 |
|------|--------|--------|------|
| 中国A股 | ~135行 | ~28行 | **-80%** |
| 港股 | ~105行 | ~35行 | **-67%** |
| 美股 | ~97行 | ~52行 | **-46%** |

**总共减少约 400+ 行重复代码！**

### 2. 易于扩展

添加新市场只需：
1. 创建 `settings.py`（配置）
2. 创建 `rules.py`（约30行代码）
3. 注册到 `__init__.py`

### 3. 类型安全

所有方法都有类型注解，IDE自动补全和类型检查。

### 4. 配置驱动

settings 定义一切，基类自动解析和应用。

## Services 层

### MatchingService（股票代码匹配）

```python
class MatchingService:
    @staticmethod
    def extract_stock_code(stock_id) -> str
    
    @staticmethod
    def match_stock_id(stock_id, matching) -> bool
```

### LotSizeService（整手规则）

```python
class LotSizeService:
    @staticmethod
    def parse_entries(config) -> List[LotSizeEntry]
    
    @staticmethod
    def resolve(stock_id, entries) -> LotSizeResolved
    
    @staticmethod
    def is_valid_quantity(quantity, resolved) -> bool
    
    @staticmethod
    def floor_quantity(target_quantity, resolved) -> int
```

### AmplitudeLimitService（涨跌幅限制）

```python
class AmplitudeLimitService:
    @staticmethod
    def parse_entries(config) -> List[AmplitudeLimitEntry]
    
    @staticmethod
    def resolve_ratio(stock_id, status_tags, entries) -> float
    
    @staticmethod
    def compute_limit_prices(prev_close, ratio, decimals) -> Tuple[float, float]
    
    @staticmethod
    def is_within_limit(current_price, limit_up, limit_down) -> bool
```

### SettlementService（交收规则）

```python
class SettlementService:
    @staticmethod
    def is_allowed_to_settle(days_held, t_plus) -> bool
    
    @staticmethod
    def get_settlement_period(t_plus) -> int
```

## 最佳实践

1. **简单市场**：直接使用基类默认实现
2. **特殊市场**：只覆盖需要特殊处理的方法
3. **复杂规则**：在settings中定义多规则匹配
4. **类型注解**：保持所有方法的类型注解完整

新架构清晰、简洁、易于维护和扩展！