# Strategy 数据存储方案设计 V2

**日期**: 2025-12-19  
**更新**: 基于 Legacy 系统实际使用情况

---

## 背景

### Legacy 系统的 JSON 存储结构

```
strategy/Random/tmp/
├── meta.json                     # 策略元信息（next_session_id）
├── 2026_01_05-1/                # Session 文件夹（日期-session_id）
│   ├── 0_session_summary.json   # Session 汇总（所有股票的统计）
│   ├── 601098.SH.json           # 单个股票的所有 investments
│   ├── 002773.SZ.json
│   └── ...
├── 2025_12_24-262/
└── ...
```

### 单股票 JSON 结构

```json
{
  "stock": {...},               # 股票基本信息
  "investments": [              # 所有投资记录（一个机会 = 一个 investment）
    {
      "result": "win/loss",
      "start_date": "20110422",
      "end_date": "20110509",
      "purchase_price": 11.54,
      "duration_in_days": 17,
      "overall_profit": -0.73,  # 基于固定金额（如 10 元）
      "roi": -0.063,            # 收益率（价格变化）✅
      "tracking": {...},        # 持有期间的追踪数据
      "completed_targets": [...] # 完成的目标（止盈/止损/到期）
    }
  ],
  "summary": {                  # 该股票的汇总统计
    "total_investments": 40,
    "win_rate": 0.6,
    "avg_roi": 0.01,
    ...
  }
}
```

### Session Summary 结构

```json
{
  "win_rate": 46.38,
  "avg_roi": -0.0026,
  "annual_return": -0.06,
  "total_investments": 69,
  "stocks_have_opportunities": 2,
  "roi_distribution": {...},  # ROI 分布统计
  "duration_distribution": {...}  # 持有期分布
}
```

---

## 重新评估

### 用户的核心观点

> "JSON 比较简单而且直观，在没有 UI 或 SQL 技能薄弱的情况下 JSON 是最直观的结果观察器"

**这个观点非常合理！**

#### JSON 的实际优势

1. **直观易读** ⭐⭐⭐⭐⭐
   - 可以直接打开文件查看
   - 不需要连接数据库
   - 不需要写 SQL 查询
   - 数据结构一目了然

2. **文件组织清晰** ⭐⭐⭐⭐⭐
   - 按 session 组织（每次回测一个文件夹）
   - 每个股票一个文件（易于定位）
   - 包含 summary（快速查看结果）

3. **易于分享和备份** ⭐⭐⭐⭐⭐
   - 文件可以直接复制
   - 可以压缩打包
   - 可以用 Git 版本控制

4. **开发友好** ⭐⭐⭐⭐⭐
   - 调试时可以直接查看
   - 不需要额外工具
   - IDE 可以直接打开

5. **符合现有习惯** ⭐⭐⭐⭐⭐
   - 已经有成熟的 JSON 方案
   - 用户习惯了这种方式
   - 不需要重新学习

---

## 方案重新对比

### 方案 A: 数据库（分表）

**优势**：
- ✅ 性能好（大数据量）
- ✅ 查询方便（SQL）
- ✅ 支持复杂查询

**劣势**：
- ❌ 需要连接数据库
- ❌ 需要 SQL 知识
- ❌ 不直观（需要查询才能看到）
- ❌ 难以分享（需要导出）

---

### 方案 C: JSON 文件

**优势**：
- ✅ 直观易读（最重要！）
- ✅ 无需 SQL 知识
- ✅ 易于分享和备份
- ✅ 开发友好
- ✅ 符合现有习惯

**劣势**：
- ❌ 性能较差（大数据量）
- ❌ 不支持复杂查询
- ❌ 并发写入困难

---

## 🤔 关键问题：数据量

### 实际数据量估算

**Scanner 模式**：
- 每次扫描：发现 100-1000 个机会
- 每个机会：< 1KB
- 总计：0.1MB - 1MB per scan
- **非常小！**

**Simulator 模式**：
- Legacy 示例：40 个 investments/股票
- 每个 investment：~0.5KB
- 单股票文件：~20KB
- 100 个股票：~2MB
- **也很小！**

**结论**：**数据量不大，JSON 完全可以胜任！**

---

## 混合方案：JSON + 可选数据库

### 🏆 推荐方案：JSON 为主，数据库为辅

**设计思路**：
1. **默认使用 JSON**（与 Legacy 一致）
2. **提供可选的数据库存储**（高级用户）
3. **通过配置切换**

---

### 方案详细设计

#### 1. 文件结构（JSON 模式）

```
app/userspace/strategies/momentum/
├── strategy_worker.py
├── settings.py
└── results/                     # 改名：tmp → results（更语义化）
    ├── meta.json                # 策略元信息
    ├── scan/                    # 扫描结果
    │   ├── 2025_12_19/          # 按日期组织
    │   │   ├── summary.json     # 汇总信息
    │   │   ├── 000001.SZ.json   # 单股票机会
    │   │   └── ...
    │   └── latest -> 2025_12_19/  # 软链接到最新
    │
    └── simulate/                # 模拟结果
        ├── session_001/         # Session 文件夹
        │   ├── summary.json     # Session 汇总
        │   ├── 000001.SZ.json   # 单股票回测结果
        │   └── ...
        └── latest -> session_001/  # 软链接到最新
```

**关键改进**：
1. ✅ `tmp` → `results`（更语义化）
2. ✅ 分离 `scan/` 和 `simulate/`（职责清晰）
3. ✅ 添加 `latest` 软链接（快速访问最新结果）
4. ✅ 扫描按日期组织（更直观）

---

#### 2. Opportunity JSON 结构（新设计）

**Scanner 输出**：`scan/2025_12_19/000001.SZ.json`

```json
{
  "stock": {
    "id": "000001.SZ",
    "name": "平安银行"
  },
  "opportunities": [
    {
      "opportunity_id": "uuid-1",
      "trigger_date": "20251219",
      "trigger_price": 10.50,
      "trigger_conditions": {
        "momentum": 0.08,
        "volume_ratio": 1.5
      },
      "expected_return": 0.10,
      "confidence": 0.75,
      "status": "active",
      "created_at": "2025-12-19T10:30:00"
    }
  ],
  "summary": {
    "total_opportunities": 1,
    "avg_expected_return": 0.10
  }
}
```

**Simulator 输出**：`simulate/session_001/000001.SZ.json`

```json
{
  "stock": {
    "id": "000001.SZ",
    "name": "平安银行"
  },
  "opportunities": [
    {
      "opportunity_id": "uuid-1",
      "trigger_date": "20251219",
      "trigger_price": 10.50,
      "trigger_conditions": {...},
      
      // ===== Simulator 添加的字段 =====
      "sell_date": "20251230",
      "sell_price": 11.20,
      "sell_reason": "take_profit",
      "price_return": 0.0667,        // (11.20 - 10.50) / 10.50
      "holding_days": 11,
      "max_price": 11.50,
      "min_price": 10.30,
      "max_drawdown": -0.019,
      "status": "closed",
      
      // ===== 持有期追踪 =====
      "tracking": {
        "daily_prices": [10.50, 10.60, ...],  // 每日收盘价
        "daily_returns": [0, 0.01, ...],      // 每日收益率
        "max_reached_date": "20251225",
        "min_reached_date": "20251222"
      }
    }
  ],
  "summary": {
    "total_opportunities": 1,
    "win_rate": 1.0,
    "avg_price_return": 0.0667,
    "avg_holding_days": 11
  }
}
```

---

#### 3. Session Summary（汇总）

**Scanner**: `scan/2025_12_19/summary.json`

```json
{
  "scan_date": "2025-12-19",
  "strategy_name": "momentum",
  "strategy_version": "1.0",
  "total_stocks_scanned": 1000,
  "total_opportunities_found": 50,
  "opportunity_rate": 0.05,
  "avg_expected_return": 0.08,
  "top_opportunities": [
    {
      "stock_id": "000001.SZ",
      "expected_return": 0.15,
      "confidence": 0.85
    }
  ]
}
```

**Simulator**: `simulate/session_001/summary.json`

```json
{
  "session_id": "session_001",
  "session_date": "2025-12-19",
  "strategy_name": "momentum",
  "strategy_version": "1.0",
  
  // ===== 统计信息 =====
  "total_opportunities": 50,
  "total_closed": 50,
  "win_rate": 0.65,
  "avg_price_return": 0.05,
  "annual_return": 0.30,
  "avg_holding_days": 15,
  
  // ===== 收益分布 =====
  "return_distribution": {
    "lt_-10pct": 2,
    "-10_to_-5pct": 5,
    "-5_to_0pct": 10,
    "0_to_5pct": 15,
    "5_to_10pct": 12,
    "10_to_15pct": 4,
    "gt_15pct": 2
  },
  
  // ===== 持有期分布 =====
  "duration_distribution": {
    "1_to_5_days": 5,
    "6_to_10_days": 10,
    "11_to_20_days": 25,
    "21_to_30_days": 8,
    "gt_30_days": 2
  }
}
```

---

#### 4. 配置选项

**settings.py**：

```python
settings = {
    "name": "momentum",
    "version": "1.0",
    
    # ... 其他配置 ...
    
    "storage": {
        "mode": "json",              # json / database / both
        "json_path": "results",      # JSON 文件路径
        "compress_old_sessions": True,  # 自动压缩旧 session
        "keep_recent_sessions": 10   # 保留最近 10 个 session
    }
}
```

---

#### 5. 数据服务接口（统一抽象）

```python
class OpportunityService:
    """Opportunity 数据服务（支持多种存储）"""
    
    def __init__(self, strategy_name: str, settings: dict):
        self.strategy_name = strategy_name
        self.storage_mode = settings['storage']['mode']
        
        if self.storage_mode in ['json', 'both']:
            self.json_storage = JsonOpportunityStorage(strategy_name, settings)
        
        if self.storage_mode in ['database', 'both']:
            self.db_storage = DatabaseOpportunityStorage(strategy_name)
    
    def save_opportunity(self, opportunity: Opportunity):
        """保存机会（根据配置选择存储）"""
        if self.storage_mode in ['json', 'both']:
            self.json_storage.save(opportunity)
        
        if self.storage_mode in ['database', 'both']:
            self.db_storage.save(opportunity)
    
    def load_opportunities(self, session_id: str = None) -> List[Opportunity]:
        """加载机会"""
        if self.storage_mode == 'json':
            return self.json_storage.load(session_id)
        elif self.storage_mode == 'database':
            return self.db_storage.load(session_id)
        else:  # both - 优先从 JSON 加载
            return self.json_storage.load(session_id)
```

---

### JSON 存储实现

```python
class JsonOpportunityStorage:
    """JSON 文件存储"""
    
    def __init__(self, strategy_name: str, settings: dict):
        self.strategy_name = strategy_name
        self.base_path = Path(f"app/userspace/strategies/{strategy_name}/results")
        self.scan_path = self.base_path / "scan"
        self.simulate_path = self.base_path / "simulate"
    
    def save_scan_opportunity(self, opportunity: Opportunity):
        """保存扫描结果"""
        date = opportunity.scan_date
        dir_path = self.scan_path / date
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / f"{opportunity.stock_id}.json"
        
        # 读取现有数据（如果存在）
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
        else:
            data = {
                "stock": {"id": opportunity.stock_id, "name": opportunity.stock_name},
                "opportunities": [],
                "summary": {}
            }
        
        # 添加新机会
        data['opportunities'].append(opportunity.to_dict())
        
        # 更新 summary
        data['summary'] = self._calculate_summary(data['opportunities'])
        
        # 保存
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 更新 latest 软链接
        latest_link = self.scan_path / "latest"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(date, target_is_directory=True)
    
    def save_simulate_opportunity(self, opportunity: Opportunity, session_id: str):
        """保存模拟结果"""
        dir_path = self.simulate_path / session_id
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / f"{opportunity.stock_id}.json"
        
        # 类似 scan，保存到文件
        # ...
    
    def load_scan_opportunities(self, date: str = None) -> List[Opportunity]:
        """加载扫描结果"""
        if date is None:
            # 加载最新
            latest_link = self.scan_path / "latest"
            if not latest_link.exists():
                return []
            date = latest_link.resolve().name
        
        dir_path = self.scan_path / date
        if not dir_path.exists():
            return []
        
        opportunities = []
        for file_path in dir_path.glob("*.json"):
            if file_path.name == "summary.json":
                continue
            with open(file_path, 'r') as f:
                data = json.load(f)
            for opp_dict in data['opportunities']:
                opportunities.append(Opportunity.from_dict(opp_dict))
        
        return opportunities
```

---

## 最终建议

### 🏆 采用混合方案：JSON 为主 + 数据库可选

**理由**：

1. **默认 JSON**：
   - ✅ 直观易读（最重要）
   - ✅ 符合用户习惯
   - ✅ 无需 SQL 知识
   - ✅ 数据量小，性能足够

2. **可选数据库**：
   - ✅ 高级用户可以选择
   - ✅ 支持复杂查询
   - ✅ 适合大数据量

3. **统一接口**：
   - ✅ 用户无感知
   - ✅ 易于切换
   - ✅ 可以同时使用（both）

---

### 实施步骤

1. **Phase 1：JSON 存储**
   - 实现 `JsonOpportunityStorage`
   - 支持 Scanner 和 Simulator
   - 生成 summary
   - 添加 `latest` 软链接

2. **Phase 2：数据服务抽象**
   - 实现 `OpportunityService`（统一接口）
   - 支持多种存储模式

3. **Phase 3：可选数据库**
   - 实现 `DatabaseOpportunityStorage`
   - 支持通过配置切换

4. **Phase 4：工具支持**
   - JSON → 数据库迁移工具
   - 数据库 → JSON 导出工具
   - 自动压缩旧 session

---

### 与 Legacy 的兼容性

**保持兼容**：
- ✅ 文件结构类似（tmp → results）
- ✅ JSON 格式兼容（可以读取旧数据）
- ✅ 用户习惯不变

**改进**：
- ✅ 更清晰的文件组织（scan / simulate）
- ✅ 添加软链接（快速访问最新）
- ✅ 统一的 summary 格式

---

## 对比表（最终版）

| 维度 | 数据库（分表） | JSON 文件 | 混合方案 |
|------|---------------|----------|---------|
| **直观性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **易用性** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **性能** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **查询能力** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **分享备份** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **开发友好** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **符合习惯** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **灵活性** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

**文档结束**
