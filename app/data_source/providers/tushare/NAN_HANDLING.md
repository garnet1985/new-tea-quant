# NaN/NULL 处理配置文档

## 📋 默认行为

**无需任何配置**，框架会自动从表schema获取字段类型，并根据类型处理NaN：

| 字段类型 | NaN → 默认值 | 示例 |
|---------|-------------|------|
| float, double, decimal | 0 | price: NaN → 0.0 |
| int, bigint, tinyint | 0 | volume: NaN → 0 |
| varchar, text | '' (空字符串) | name: NaN → '' |
| datetime, date | None | date: NaN → None |

**目的：** 确保所有表中不出现NaN/NULL，避免数据库错误。

---

## 🔧 扩展配置

如果需要特殊处理，可以在config中添加 `nan_handling` 配置：

### **场景1: 关闭自动转换（保留所有NaN为NULL）**

```python
CONFIG = {
    'table_name': 'my_table',
    
    'nan_handling': {
        'auto_convert': False  # 关闭自动转换
    }
}

# 结果：
# price: NaN → None (不转换为0)
# name: NaN → None (不转换为'')
```

**用途：**
- 数据库schema允许NULL
- 需要区分"0"和"无数据"
- 需要保留原始的缺失状态

---

### **场景2: 指定某些字段允许NULL**

```python
CONFIG = {
    'table_name': 'stock_data',
    
    'nan_handling': {
        'allow_null_fields': ['optional_indicator', 'beta', 'alpha']
    }
}

# 结果：
# price: NaN → 0 (默认行为)
# volume: NaN → 0 (默认行为)
# optional_indicator: NaN → None (允许NULL)
# beta: NaN → None (允许NULL)
```

**用途：**
- 某些可选指标允许为空
- 区分"0"（真实值）和"NULL"（无数据）

---

### **场景3: 自定义字段的默认值**

```python
CONFIG = {
    'table_name': 'analysis_result',
    
    'nan_handling': {
        'field_defaults': {
            'risk_score': -1,        # 风险评分：NaN → -1（表示未计算）
            'grade': 'unrated',      # 评级：NaN → 'unrated'
            'confidence': 0.0,       # 置信度：NaN → 0.0
        }
    }
}

# 结果：
# risk_score: NaN → -1 (自定义)
# grade: NaN → 'unrated' (自定义)
# confidence: NaN → 0.0 (自定义)
# price: NaN → 0 (默认行为，因为未在field_defaults中配置)
```

**用途：**
- 使用特殊值标记"未计算"或"无效"
- 与业务逻辑集成（如-1表示未评分）

---

### **场景4: 混合配置**

```python
CONFIG = {
    'table_name': 'complex_data',
    
    'nan_handling': {
        # 允许某些字段为NULL
        'allow_null_fields': ['optional_field1', 'optional_field2'],
        
        # 自定义某些字段的默认值
        'field_defaults': {
            'status': 'unknown',
            'score': -999,  # 使用-999表示无效值
        }
        
        # 其他字段使用默认行为（根据schema类型）
    }
}

# 处理优先级：
# 1. field_defaults中的配置（最高优先级）
# 2. allow_null_fields中的字段（保留NULL）
# 3. schema类型的默认行为（最低优先级）
```

---

## 📊 完整示例

### **示例：股票分析表（允许部分NULL）**

```python
CONFIG = {
    'table_name': 'stock_analysis',
    'renew_mode': 'upsert',
    
    'nan_handling': {
        # 技术指标允许为NULL（某些日期可能无法计算）
        'allow_null_fields': [
            'ma5', 'ma10', 'ma20',  # 移动平均线（数据不足时为NULL）
            'rsi', 'macd',           # 技术指标
            'predicted_price'        # 预测价格（可能未计算）
        ],
        
        # 特殊字段使用自定义默认值
        'field_defaults': {
            'confidence_level': 0.0,  # 置信度默认0
            'rating': 'unrated',      # 评级默认unrated
            'risk_level': -1          # 风险等级-1表示未评估
        }
    },
    
    'apis': [...]
}
```

### **示例：严格模式（完全关闭转换）**

```python
CONFIG = {
    'table_name': 'raw_data',
    
    'nan_handling': {
        'auto_convert': False  # 完全保留原始NaN
    }
}

# 适用于：
# - 数据预处理阶段
# - 需要后续分析NaN的位置和原因
# - 数据库schema允许NULL
```

---

## 🎯 配置决策树

```
需要特殊处理NaN？
│
├─ No → 不配置nan_handling（使用默认行为）
│   └─ 数值→0, 字符串→'', 其他→None
│
└─ Yes → 添加nan_handling配置
    │
    ├─ 所有字段都保留NULL？
    │   └─ 'auto_convert': False
    │
    ├─ 某些字段保留NULL？
    │   └─ 'allow_null_fields': [...]
    │
    ├─ 某些字段用特殊值？
    │   └─ 'field_defaults': {field: value}
    │
    └─ 混合需求？
        └─ 同时配置多个选项
```

---

## 💡 最佳实践

1. **默认就够用** - 80%的场景不需要配置
2. **明确意图** - 如果允许NULL，在注释中说明原因
3. **特殊值有意义** - 使用-1、-999等明确表示"未知"而非"零"
4. **保持一致** - 同类型的表使用相同的NaN处理策略

---

## 📝 处理优先级

```
1. field_defaults (最高优先级)
   ↓ 如果字段在field_defaults中，使用自定义值
   
2. allow_null_fields
   ↓ 如果字段在allow_null_fields中，保留None
   
3. schema类型 (默认行为)
   ↓ 根据字段类型自动决定
```

---

## 🔍 调试技巧

如果想查看NaN转换的结果：

```python
class MyRenewer(BaseRenewer):
    def save_data(self, data):
        # 在保存前打印数据
        import pandas as pd
        df = self.to_df(data)
        
        # 检查NaN
        logger.info(f"NaN统计：\n{df.isna().sum()}")
        
        # 检查转换后的值
        logger.info(f"数值字段最小值：\n{df[['price', 'volume']].min()}")
        
        return super().save_data(data)
```
