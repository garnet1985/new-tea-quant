# Tag 系统 Entity 设计实现方案

## 📋 设计原则

**分层设计**：
- **工程级别**：支持通用 entity（数据库、模型层保持灵活性）
- **框架级别**：默认只支持股票（简化使用，降低学习成本）
- **扩展级别**：高级用户可以通过接口自定义 entity（提供扩展能力）

## 🎯 设计优势

### 1. **保持灵活性** ⭐⭐⭐⭐⭐
- ✅ 数据库层支持 `entity_id`（可以是股票、指数等）
- ✅ 模型层支持通用查询
- ✅ 未来扩展不需要改数据库结构

### 2. **简化默认使用** ⭐⭐⭐⭐⭐
- ✅ 框架默认只支持股票
- ✅ 配置更简单（`base_term` 而不是 `base_entity`）
- ✅ 文档和示例只讲股票场景
- ✅ 降低学习成本

### 3. **提供扩展能力** ⭐⭐⭐⭐
- ✅ 高级用户可以通过接口扩展
- ✅ 复杂度转移给高级用户
- ✅ 不影响默认用户的使用

## 💡 实现方案

### 1. 配置层：`base_term` 替代 `base_entity`

```python
TAG_CONFIG = {
    "meta": {...},
    "required_data": ["kline", "corporate_finance"],
    
    # ✅ 改为 base_term（明确是股票相关的）
    "base_term": "kline",  # 或 "stock_base_term"
    # 说明：
    # - 明确表示这是股票相关的迭代粒度
    # - 系统默认只支持股票
    # - 如果是股票，entity_id 就是股票代码
    
    "execution": {...},
    "core": {...},
    "performance": {...},
}
```

**优势**：
- 命名更清晰（`base_term` 比 `base_entity` 更明确）
- 暗示这是股票相关的配置
- 降低用户理解成本

### 2. Calculator 接口：提供数据加载扩展点

```python
class BaseTagCalculator(ABC):
    """Tag Calculator 基类"""
    
    def __init__(self, tag_id: int, tag_config: Dict[str, Any], data_mgr, data_source_mgr=None):
        self.tag_id = tag_id
        self.tag_config = tag_config
        self.data_mgr = data_mgr
        self.data_source_mgr = data_source_mgr  # ✅ 提供 DataSourceManager 实例
    
    # ========================================================================
    # 数据加载接口（可扩展）
    # ========================================================================
    
    def load_entity_data(
        self, 
        entity_id: str, 
        required_data: List[str],
        as_of_date: str
    ) -> Dict[str, Any]:
        """
        加载实体历史数据（可扩展接口）
        
        默认实现：只支持股票
        - entity_id 就是股票代码
        - 从 data_source 系统加载股票数据
        
        高级用户扩展：
        - 重写此方法，支持其他 entity（指数、板块等）
        - 使用 self.data_source_mgr 加载自定义数据
        
        Args:
            entity_id: 实体ID（默认是股票代码）
            required_data: 需要的数据源列表（如 ["kline", "corporate_finance"]）
            as_of_date: 当前时间点（用于过滤历史数据）
            
        Returns:
            Dict[str, Any]: 历史数据字典
                - klines: List[Dict] - K线数据
                - finance: List[Dict] - 财务数据
                - ... 其他数据
        """
        # ✅ 默认实现：只支持股票
        historical_data = {}
        
        for data_source in required_data:
            if data_source == "kline":
                # 加载股票K线数据
                kline_model = self.data_mgr.get_model("stock_kline")
                klines = kline_model.load_by_stock(entity_id, end_date=as_of_date)
                historical_data["klines"] = klines
                
            elif data_source == "corporate_finance":
                # 加载股票财务数据
                finance_model = self.data_mgr.get_model("corporate_finance")
                finance = finance_model.load_by_stock(entity_id, end_date=as_of_date)
                historical_data["finance"] = finance
                
            # ... 其他数据源
        
        return historical_data
    
    # ========================================================================
    # 计算接口（用户实现）
    # ========================================================================
    
    @abstractmethod
    def calculate_tag(
        self, 
        stock_id: str,  # ✅ 明确是股票代码（默认场景）
        as_of_date: str, 
        historical_data: Dict[str, Any]
    ) -> Optional[TagEntity]:
        """
        计算 tag（用户实现）
        
        Args:
            stock_id: 股票代码（如 "000001.SZ"）
            as_of_date: 当前时间点（YYYYMMDD）
            historical_data: 历史数据（由 load_entity_data 加载）
            
        Returns:
            TagEntity 或 None
        """
        pass
```

### 3. 高级用户扩展示例

```python
class IndexTagCalculator(BaseTagCalculator):
    """指数 Tag Calculator（高级用户扩展）"""
    
    def load_entity_data(
        self, 
        entity_id: str,  # 这里是指数代码（如 "000300.SH"）
        required_data: List[str],
        as_of_date: str
    ) -> Dict[str, Any]:
        """
        重写数据加载方法，支持指数数据
        
        注意：这是高级用法，需要用户自己实现数据加载逻辑
        """
        historical_data = {}
        
        # 使用 data_source_mgr 加载指数数据
        if "index_kline" in required_data:
            # 从 data_source 系统加载指数K线数据
            index_data = await self.data_source_mgr.fetch("index_kline", context={
                "index_code": entity_id,
                "end_date": as_of_date
            })
            historical_data["index_klines"] = index_data.get("data", [])
        
        return historical_data
    
    def calculate_tag(
        self, 
        entity_id: str,  # 指数代码
        as_of_date: str, 
        historical_data: Dict[str, Any]
    ) -> Optional[TagEntity]:
        """计算指数 tag"""
        # 使用指数数据计算 tag
        ...
```

### 4. TagExecutor 调用流程

```python
class TagExecutor:
    """Tag 执行器"""
    
    async def execute_tag(self, tag_config: Dict, stock_list: List[str]):
        """
        执行 tag 计算
        
        默认流程（只支持股票）：
        1. 遍历股票列表
        2. 对每个股票调用 calculator.calculate_tag()
        3. 使用默认的 load_entity_data 加载股票数据
        """
        calculator = self._load_calculator(tag_config)
        
        for stock_id in stock_list:  # ✅ 默认是股票列表
            # 加载历史数据（使用默认实现或用户扩展的实现）
            historical_data = calculator.load_entity_data(
                entity_id=stock_id,  # 股票代码
                required_data=tag_config["required_data"],
                as_of_date=current_date
            )
            
            # 调用计算接口
            tag_entity = calculator.calculate_tag(
                stock_id=stock_id,
                as_of_date=current_date,
                historical_data=historical_data
            )
            
            # 保存 tag（entity_id 就是 stock_id）
            if tag_entity:
                self._save_tag_value(
                    entity_id=stock_id,  # ✅ 数据库层仍然支持 entity_id
                    tag_id=tag_config["meta"]["tag_id"],
                    tag_entity=tag_entity
                )
```

## 📊 配置对比

### 之前（通用 entity）
```python
"base_entity": "kline",  # 需要理解 entity 概念
```

### 之后（默认股票，可扩展）
```python
"base_term": "kline",  # ✅ 明确是股票相关的迭代粒度
# 默认 entity 是股票，entity_id 就是股票代码
# 高级用户可以通过 Calculator 扩展支持其他 entity
```

## 🎯 实现建议

### 1. **配置层**
- ✅ `base_entity` → `base_term` 或 `stock_base_term`
- ✅ 文档明确说明：默认只支持股票
- ✅ 示例只展示股票场景

### 2. **Calculator 基类**
- ✅ 提供 `load_entity_data()` 接口（默认实现只支持股票）
- ✅ `calculate_tag()` 参数改为 `stock_id`（默认场景）
- ✅ 文档说明如何扩展支持其他 entity

### 3. **TagExecutor**
- ✅ 默认遍历股票列表
- ✅ 调用 `calculator.load_entity_data()` 加载数据
- ✅ 保存时 `entity_id` 就是 `stock_id`

### 4. **文档**
- ✅ 主文档只讲股票场景
- ✅ 单独章节说明高级扩展（如何支持其他 entity）
- ✅ 提供扩展示例代码

## ✅ 总结

**这个设计非常好**，理由：

1. **保持灵活性**：数据库层支持通用 entity，未来扩展不需要改结构
2. **简化默认使用**：框架默认只支持股票，配置和文档更简单
3. **提供扩展能力**：高级用户可以通过 `load_entity_data` 接口扩展
4. **复杂度转移**：默认用户简单，高级用户有扩展能力

**实施步骤**：
1. 配置：`base_entity` → `base_term`
2. Calculator：添加 `load_entity_data()` 接口（默认实现只支持股票）
3. 文档：主文档只讲股票，单独章节讲扩展
4. 示例：只提供股票示例，扩展示例放在高级章节
