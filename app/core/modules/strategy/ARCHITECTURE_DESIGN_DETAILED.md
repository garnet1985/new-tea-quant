# Strategy 模块架构设计 - 详细决策

## 📊 决策分析

### 1. Investment 的粒度分析

#### 交叉部分分析

**PriceFactorInvestment 字段**（来自 `investment_builder.py`）：
- 基础信息：`start_date`, `end_date`, `purchase_price`, `duration_in_days`
- 收益信息：`overall_profit`, `roi`, `overall_annual_return`
- 状态：`result` (win/loss/open)
- 详细追踪：`tracking` (max/min price), `completed_targets`

**CapitalAllocationInvestment 字段**（来自 `capital_allocation_simulator.py`）：
- 基础信息：`buy_date`, `sell_date`, `buy_price`, `sell_price`, `shares`
- 收益信息：`realized_pnl`, `roi`
- 费用信息：`commission`, `stamp_duty`, `transfer_fee`, `total_cost`, `avg_cost`
- 状态：`status` (open/closed)

**共同部分**（约 60-70% 重叠）：
```python
# 共同字段
- investment_id / opportunity_id
- stock_id / stock_name
- buy_date / start_date
- sell_date / end_date
- buy_price / purchase_price
- sell_price
- profit / overall_profit / realized_pnl
- roi
- holding_days / duration_in_days
- status / result
```

**差异部分**：
- PF：`tracking`, `completed_targets`, `overall_annual_return`（价格追踪细节）
- CA：`shares`, `avg_cost`, `commission`, `stamp_duty`, `transfer_fee`, `total_cost`（费用和股数）

#### 建议：统一基类 + 子类扩展

**理由**：
1. **交叉部分大**（60-70%），统一基类可以复用大量代码
2. **差异部分明确**，通过子类扩展不会造成混乱
3. **便于统一统计**，可以基于基类接口进行汇总分析
4. **类型安全**，使用 dataclass 和类型提示

**设计**：

```python
# models/investment.py

@dataclass
class BaseInvestment:
    """投资基类（统一接口）"""
    # 核心标识
    investment_id: str
    opportunity_id: str
    stock_id: str
    stock_name: str
    
    # 时间信息（统一命名）
    buy_date: str
    sell_date: Optional[str] = None
    
    # 价格信息（统一命名）
    buy_price: float
    sell_price: Optional[float] = None
    
    # 收益信息（统一命名）
    profit: float = 0.0  # 总盈亏
    roi: float = 0.0     # 收益率
    holding_days: int = 0
    
    # 状态
    status: str = 'open'  # open / closed / win / loss
    
    # 抽象方法（子类实现）
    @classmethod
    @abstractmethod
    def from_source(cls, source: Any) -> 'BaseInvestment':
        """从源数据创建 Investment"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（统一接口）"""
        return asdict(self)

@dataclass
class PriceFactorInvestment(BaseInvestment):
    """价格因子投资记录"""
    # PF 特有字段
    tracking: Optional[Dict[str, Any]] = None
    completed_targets: List[Dict[str, Any]] = field(default_factory=list)
    overall_annual_return: float = 0.0
    
    # 固定值
    shares: int = 1
    
    @classmethod
    def from_opportunity(cls, opportunity: Dict[str, Any], targets: List[Dict[str, Any]]) -> 'PriceFactorInvestment':
        """从 Opportunity 和 Targets 创建"""
        # 复用现有的 InvestmentBuilder 逻辑
        pass

@dataclass
class CapitalAllocationInvestment(BaseInvestment):
    """资金分配投资记录"""
    # CA 特有字段
    shares: int
    avg_cost: float
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0
    total_cost: float = 0.0
    realized_pnl: float = 0.0
    
    @classmethod
    def from_trades(cls, buy_trade: 'Trade', sell_trades: List['Trade']) -> 'CapitalAllocationInvestment':
        """从交易记录创建"""
        # 合并买入和卖出交易
        pass
```

---

### 2. Result 的格式分析

#### 交叉部分分析

**PriceFactorSimulator Result**（来自 `result_aggregator.py`）：
```python
{
    "win_rate": float,
    "avg_roi": float,
    "annual_return": float,
    "annual_return_in_trading_days": float,
    "avg_duration_in_days": float,
    "total_investments": int,
    "total_open_investments": int,
    "total_win_investments": int,
    "total_loss_investments": int,
    "total_profit": float,
    "stocks_have_opportunities": int,
}
```

**CapitalAllocationSimulator Result**（来自 `capital_allocation_simulator.py`）：
```python
{
    "initial_capital": float,
    "final_cash": float,
    "final_equity": float,
    "total_return": float,
    "max_drawdown": float,
    "total_trades": int,
    "buy_trades": int,
    "sell_trades": int,
    "win_trades": int,
    "loss_trades": int,
    "win_rate": float,
    "total_pnl": float,
    "stock_summary": Dict,
}
```

**共同部分**（约 40-50% 重叠）：
- `win_rate`
- `total_profit` / `total_pnl`
- 元信息（策略名、版本等）

**差异部分**：
- PF：`avg_roi`, `annual_return`, `total_investments`（投资视角）
- CA：`total_return`, `max_drawdown`, `total_trades`, `equity_curve`（账户视角）

#### 建议：统一基类 + 子类扩展

**理由**：
1. **有共同部分**（40-50%），统一基类有价值
2. **差异明显**，但可以通过扩展字段支持
3. **便于对比分析**，统一接口可以对比不同模拟器的结果

**设计**：

```python
# models/result.py

@dataclass
class BaseSimulationResult:
    """模拟结果基类"""
    # 元信息（共同）
    strategy_name: str
    simulator_type: str  # 'price_factor' or 'capital_allocation'
    version_id: str
    created_at: str
    sot_version: str
    
    # 统计信息（共同）
    win_rate: float = 0.0
    total_profit: float = 0.0
    
    # 抽象方法
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

@dataclass
class PriceFactorResult(BaseSimulationResult):
    """价格因子模拟结果"""
    # PF 特有字段
    avg_roi: float = 0.0
    annual_return: float = 0.0
    annual_return_in_trading_days: float = 0.0
    avg_duration_in_days: float = 0.0
    total_investments: int = 0
    total_open_investments: int = 0
    total_win_investments: int = 0
    total_loss_investments: int = 0
    stocks_have_opportunities: int = 0
    
    # 详细数据
    stock_summaries: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class CapitalAllocationResult(BaseSimulationResult):
    """资金分配模拟结果"""
    # CA 特有字段
    initial_capital: float = 0.0
    final_cash: float = 0.0
    final_equity: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    
    # 详细数据
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    stock_summary: Dict[str, Any] = field(default_factory=dict)
```

---

### 3. Managers 的实例化方式

#### 分析

**静态方法 vs 实例方法**：

| 维度 | 静态方法 | 实例方法 |
|------|---------|---------|
| **执行效率** | ✅ 更高（无实例创建） | ⚠️ 略低（需要创建实例） |
| **代码可读性** | ✅ 清晰（工具类风格） | ⚠️ 需要管理实例生命周期 |
| **状态管理** | ❌ 无法维护状态 | ✅ 可以维护状态（缓存等） |
| **测试** | ✅ 简单（直接调用） | ⚠️ 需要 mock 实例 |
| **多线程安全** | ✅ 天然安全 | ⚠️ 需要线程安全设计 |

#### 建议：混合方式（静态方法为主 + 实例方法用于有状态的场景）

**理由**：
1. **大部分 Managers 无状态**（VersionManager, ResultManager），适合静态方法
2. **部分 Managers 需要状态**（DataLoader 需要缓存），适合实例方法
3. **执行效率优先**，静态方法更高效
4. **代码简洁**，工具类风格更清晰

**设计**：

```python
# managers/version_manager.py

class VersionManager:
    """版本管理器（静态方法）"""
    
    @staticmethod
    def resolve_sot_version(strategy_name: str, sot_version: str) -> Path:
        """解析 SOT 版本目录"""
        pass
    
    @staticmethod
    def create_simulator_version(strategy_name: str, simulator_type: str) -> Tuple[Path, int]:
        """创建模拟器版本目录"""
        pass

# managers/data_loader.py

class DataLoader:
    """数据加载器（实例方法，需要缓存）"""
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}  # 缓存策略的枚举结果
    
    def load_opportunities(self, sot_version_dir: Path, stock_id: Optional[str] = None) -> List[Dict]:
        """加载机会数据（带缓存）"""
        cache_key = f"{sot_version_dir}_{stock_id}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        # 加载数据
        data = self._load_from_file(sot_version_dir, stock_id)
        
        if self.cache_enabled:
            self._cache[cache_key] = data
        
        return data
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
```

---

### 4. 数据加载缓存

#### 澄清

**你的理解**：一次只能缓存一个策略的枚举结果 ✅

**建议**：支持单策略缓存，通过 `DataLoader` 实例管理

**设计**：

```python
# managers/data_loader.py

class DataLoader:
    """数据加载器（单策略缓存）"""
    
    def __init__(self, strategy_name: str, cache_enabled: bool = True):
        self.strategy_name = strategy_name
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}  # 缓存当前策略的数据
    
    def load_opportunities_and_targets(
        self, 
        sot_version_dir: Path, 
        stock_id: Optional[str] = None
    ) -> Dict[str, List]:
        """
        加载机会和目标数据
        
        缓存策略：
        - 缓存 key: f"{sot_version_dir.name}_{stock_id or 'all'}"
        - 只缓存当前策略的数据
        - 切换策略时需要创建新的 DataLoader 实例
        """
        cache_key = f"{sot_version_dir.name}_{stock_id or 'all'}"
        
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        # 加载数据
        opportunities = self._load_opportunities_from_csv(sot_version_dir, stock_id)
        targets = self._load_targets_from_csv(sot_version_dir, stock_id)
        
        data = {
            'opportunities': opportunities,
            'targets': targets,
        }
        
        if self.cache_enabled:
            self._cache[cache_key] = data
        
        return data
    
    def clear_cache(self):
        """清空缓存（切换策略时调用）"""
        self._cache.clear()
```

**使用方式**：

```python
# 在模拟器中
data_loader = DataLoader(strategy_name="example", cache_enabled=True)
data = data_loader.load_opportunities_and_targets(sot_version_dir)

# 切换策略时
data_loader.clear_cache()
data_loader.strategy_name = "another_strategy"
```

---

### 5. 数据存储管理（文件级别）

#### 分析三个选项

**Option 1: ResultManager 管理数据存取**

**优点**：
- ✅ 职责清晰：结果管理器负责结果的保存和加载
- ✅ 统一接口：所有结果文件通过 ResultManager 管理

**缺点**：
- ❌ 职责过重：ResultManager 既要管理结果格式，又要管理文件 I/O
- ❌ 命名混淆：ResultManager 听起来像是管理结果对象，不是文件

**Option 2: VersionManager 管理数据存取**

**优点**：
- ✅ 版本相关：版本目录和文件存储确实相关
- ✅ 统一管理：版本和文件都在一个地方

**缺点**：
- ❌ 职责混乱：VersionManager 应该专注于版本管理，不应该处理文件 I/O
- ❌ 耦合度高：版本管理和文件存储耦合在一起

**Option 3: 单独的 DataStorageManager**

**优点**：
- ✅ **职责单一**：专门负责文件级别的数据存取
- ✅ **清晰明确**：命名清晰，职责明确
- ✅ **易于扩展**：可以支持多种存储后端（文件、数据库等）
- ✅ **解耦**：与版本管理、结果管理解耦

**缺点**：
- ⚠️ 多一个 Manager：但这是值得的，因为职责更清晰

#### 建议：Option 3 + ResultManager 协作

**理由**：
1. **职责分离**：DataStorageManager 负责文件 I/O，ResultManager 负责结果对象管理
2. **易于测试**：可以分别测试文件操作和结果对象
3. **易于扩展**：未来可以支持数据库存储等

**设计**：

```python
# managers/data_storage_manager.py

class DataStorageManager:
    """数据存储管理器（文件级别）"""
    
    def __init__(self, version_dir: Path):
        """
        初始化数据存储管理器
        
        Args:
            version_dir: 版本目录路径
        """
        self.version_dir = version_dir
        self.version_dir.mkdir(parents=True, exist_ok=True)
    
    # ===== 机会和目标数据 =====
    
    def save_opportunities(self, opportunities: List[Dict[str, Any]], stock_id: Optional[str] = None) -> Path:
        """保存机会 CSV"""
        if stock_id:
            filename = f"{stock_id}_opportunities.csv"
        else:
            filename = "opportunities.csv"
        
        file_path = self.version_dir / filename
        # 保存逻辑
        return file_path
    
    def load_opportunities(self, stock_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """加载机会 CSV"""
        if stock_id:
            filename = f"{stock_id}_opportunities.csv"
        else:
            filename = "opportunities.csv"
        
        file_path = self.version_dir / filename
        # 加载逻辑
        return []
    
    def save_targets(self, targets: List[Dict[str, Any]], stock_id: Optional[str] = None) -> Path:
        """保存目标 CSV"""
        pass
    
    def load_targets(self, stock_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """加载目标 CSV"""
        pass
    
    # ===== 投资和交易数据 =====
    
    def save_investments(self, investments: List[BaseInvestment], format: str = 'json') -> Path:
        """保存投资记录"""
        if format == 'json':
            file_path = self.version_dir / "investments.json"
            # 保存 JSON
        else:
            file_path = self.version_dir / "investments.csv"
            # 保存 CSV
        return file_path
    
    def load_investments(self, format: str = 'json') -> List[Dict[str, Any]]:
        """加载投资记录"""
        pass
    
    def save_trades(self, trades: List[Trade]) -> Path:
        """保存交易记录"""
        file_path = self.version_dir / "trades.json"
        # 保存逻辑
        return file_path
    
    def load_trades(self) -> List[Dict[str, Any]]:
        """加载交易记录"""
        pass
    
    # ===== 结果数据 =====
    
    def save_summary(self, summary: Dict[str, Any], filename: str = "summary.json") -> Path:
        """保存汇总结果"""
        file_path = self.version_dir / filename
        # 保存逻辑
        return file_path
    
    def load_summary(self, filename: str = "summary.json") -> Dict[str, Any]:
        """加载汇总结果"""
        pass
    
    def save_equity_curve(self, equity_curve: List[Dict[str, Any]]) -> Path:
        """保存权益曲线"""
        file_path = self.version_dir / "equity_curve.json"
        # 保存逻辑
        return file_path
    
    def load_equity_curve(self) -> List[Dict[str, Any]]:
        """加载权益曲线"""
        pass
    
    # ===== 元数据 =====
    
    def save_metadata(self, metadata: Dict[str, Any]) -> Path:
        """保存元数据"""
        file_path = self.version_dir / "metadata.json"
        # 保存逻辑
        return file_path
    
    def load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        pass

# managers/result_manager.py

class ResultManager:
    """结果管理器（结果对象级别）"""
    
    def __init__(self, storage_manager: DataStorageManager):
        """
        初始化结果管理器
        
        Args:
            storage_manager: 数据存储管理器
        """
        self.storage = storage_manager
    
    def save_simulation_result(self, result: BaseSimulationResult) -> Path:
        """保存模拟结果（使用 DataStorageManager）"""
        # 1. 保存汇总
        summary_path = self.storage.save_summary(result.to_dict(), "summary.json")
        
        # 2. 保存详细数据（根据类型）
        if isinstance(result, PriceFactorResult):
            self.storage.save_investments(result.investments)
        elif isinstance(result, CapitalAllocationResult):
            self.storage.save_trades(result.trades)
            self.storage.save_equity_curve(result.equity_curve)
        
        # 3. 保存元数据
        metadata = {
            "strategy_name": result.strategy_name,
            "simulator_type": result.simulator_type,
            "version_id": result.version_id,
            "sot_version": result.sot_version,
            "created_at": result.created_at,
        }
        self.storage.save_metadata(metadata)
        
        return summary_path
    
    def load_simulation_result(self) -> BaseSimulationResult:
        """加载模拟结果"""
        # 1. 加载元数据
        metadata = self.storage.load_metadata()
        simulator_type = metadata.get("simulator_type")
        
        # 2. 根据类型加载
        if simulator_type == "price_factor":
            return self._load_price_factor_result(metadata)
        elif simulator_type == "capital_allocation":
            return self._load_capital_allocation_result(metadata)
        else:
            raise ValueError(f"Unknown simulator type: {simulator_type}")
```

**协作关系**：

```
ResultManager (结果对象管理)
    ↓ 使用
DataStorageManager (文件 I/O)
    ↓ 操作
VersionManager (版本目录)
```

---

## 📋 最终建议总结

1. **Investment**：✅ 统一基类 + 子类扩展（交叉部分 60-70%，价值高）
2. **Result**：✅ 统一基类 + 子类扩展（交叉部分 40-50%，有价值）
3. **Managers 实例化**：✅ 混合方式（静态方法为主 + 实例方法用于有状态场景）
4. **数据加载缓存**：✅ 单策略缓存，通过 DataLoader 实例管理
5. **数据存储管理**：✅ Option 3（DataStorageManager）+ ResultManager 协作

---

## 🎯 实施优先级

1. **高优先级**：DataStorageManager（影响所有组件）
2. **中优先级**：Investment 和 Result 模型重构
3. **低优先级**：Managers 实例化方式优化
