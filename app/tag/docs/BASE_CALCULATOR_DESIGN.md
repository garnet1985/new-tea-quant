# Tag 基类设计文档

## 📋 设计目标

设计一个完整的 Tag 基类，提供：
1. 配置管理（读取、验证、处理）
2. 数据加载（钩子函数，有默认实现）
3. 迭代逻辑（根据 config 迭代，暴露钩子函数）
4. 其他钩子函数（初始化、清理、错误处理等）
5. 多线程支持

## 🎯 核心流程

```
获取config -> 验证config -> 初始化 -> 迭代 -> 迭代中调用calculate_tag -> 保存tag -> 完成
```

## 📐 基类设计

### BaseTagCalculator 基类结构

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction
from app.tag.entities import TagEntity


@dataclass
class TagEntity:
    """Tag 实体"""
    tag_id: int
    entity_type: str  # "stock", "kline_daily" 等
    entity_id: str
    value: str
    as_of_date: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class BaseTagCalculator(ABC):
    """Tag Calculator 基类
    
    职责：
    1. 配置管理（读取、验证、处理）
    2. 数据加载（钩子函数，默认实现支持股票）
    3. 迭代逻辑（根据 base_term 迭代）
    4. 计算钩子（calculate_tag，用户实现）
    5. 其他钩子（初始化、清理、错误处理）
    6. 多线程支持
    """
    
    def __init__(
        self, 
        tag_config: Dict[str, Any],
        data_mgr=None,
        data_source_mgr=None,
        tag_value_model=None
    ):
        """
        初始化 Calculator
        
        Args:
            tag_config: Tag 配置字典（从 config.py 加载）
            data_mgr: DataManager 实例（用于访问数据库模型）
            data_source_mgr: DataSourceManager 实例（用于加载数据源）
            tag_value_model: TagValueModel 实例（用于保存 tag 值）
        """
        self.tag_config = tag_config
        self.data_mgr = data_mgr
        self.data_source_mgr = data_source_mgr
        self.tag_value_model = tag_value_model
        
        # 验证和处理配置
        self._validate_and_process_config()
        
        # 初始化（钩子函数）
        self.on_init()
    
    # ========================================================================
    # 1. 配置管理（读取、验证、处理）
    # ========================================================================
    
    def _validate_and_process_config(self):
        """验证和处理配置"""
        # 验证必需字段
        self._validate_required_fields()
        
        # 处理默认值
        self._process_defaults()
        
        # 验证枚举值
        self._validate_enums()
        
        # 提取常用配置到实例变量（方便访问）
        self._extract_config()
    
    def _validate_required_fields(self):
        """验证必需字段"""
        required_fields = [
            "meta.name",
            "meta.display_name",
            "base_term",
        ]
        
        for field_path in required_fields:
            keys = field_path.split(".")
            value = self.tag_config
            for key in keys:
                if not isinstance(value, dict) or key not in value:
                    raise ValueError(f"配置缺少必需字段: {field_path}")
                value = value[key]
    
    def _process_defaults(self):
        """处理默认值"""
        # required_terms 默认 []
        if "required_terms" not in self.tag_config:
            self.tag_config["required_terms"] = []
        elif self.tag_config["required_terms"] is None:
            self.tag_config["required_terms"] = []
        
        # required_data 默认 []
        if "required_data" not in self.tag_config:
            self.tag_config["required_data"] = []
        
        # performance 默认值
        if "performance" not in self.tag_config:
            self.tag_config["performance"] = {}
        
        perf = self.tag_config["performance"]
        if "max_worker" not in perf:
            perf["max_worker"] = 10
        if "update_mode" not in perf:
            perf["update_mode"] = UpdateMode.INCREMENTAL.value
        if "on_version_change" not in perf:
            perf["on_version_change"] = VersionChangeAction.NEW_TAG.value
    
    def _validate_enums(self):
        """验证枚举值"""
        # 验证 base_term
        base_term = self.tag_config.get("base_term")
        valid_terms = [KlineTerm.DAILY.value, KlineTerm.WEEKLY.value, KlineTerm.MONTHLY.value]
        if base_term not in valid_terms:
            raise ValueError(f"base_term 必须是 {valid_terms} 之一，当前值: {base_term}")
        
        # 验证 required_terms
        required_terms = self.tag_config.get("required_terms", [])
        if required_terms:
            for term in required_terms:
                if term not in valid_terms:
                    raise ValueError(f"required_terms 中的值必须是 {valid_terms} 之一，当前值: {term}")
        
        # 验证 update_mode
        update_mode = self.tag_config.get("performance", {}).get("update_mode")
        valid_modes = [UpdateMode.INCREMENTAL.value, UpdateMode.REFRESH.value]
        if update_mode not in valid_modes:
            raise ValueError(f"update_mode 必须是 {valid_modes} 之一，当前值: {update_mode}")
        
        # 验证 on_version_change
        on_version_change = self.tag_config.get("performance", {}).get("on_version_change")
        valid_actions = [VersionChangeAction.NEW_TAG.value, VersionChangeAction.FULL_REFRESH.value]
        if on_version_change not in valid_actions:
            raise ValueError(f"on_version_change 必须是 {valid_actions} 之一，当前值: {on_version_change}")
    
    def _extract_config(self):
        """提取常用配置到实例变量"""
        self.tag_name = self.tag_config["meta"]["name"]
        self.display_name = self.tag_config["meta"].get("display_name", self.tag_name)
        self.base_term = self.tag_config["base_term"]
        self.required_terms = self.tag_config.get("required_terms", [])
        self.required_data = self.tag_config.get("required_data", [])
        self.core_params = self.tag_config.get("core", {})
        self.performance = self.tag_config.get("performance", {})
        self.max_worker = self.performance.get("max_worker", 10)
        self.update_mode = self.performance.get("update_mode", UpdateMode.INCREMENTAL.value)
    
    # ========================================================================
    # 2. 数据加载（钩子函数，默认实现支持股票）
    # ========================================================================
    
    def load_entity_data(
        self, 
        entity_id: str, 
        entity_type: str = "stock",
        as_of_date: str = None
    ) -> Dict[str, Any]:
        """
        加载实体历史数据（可扩展接口）
        
        默认实现：只支持股票
        - entity_id 就是股票代码（如 "000001.SZ"）
        - 从 data_source 系统加载股票数据
        
        高级用户扩展：
        - 重写此方法，支持其他 entity（指数、板块、kline 等）
        - 使用 self.data_source_mgr 加载自定义数据
        
        Args:
            entity_id: 实体ID（默认是股票代码）
            entity_type: 实体类型（默认 "stock"）
            as_of_date: 当前时间点（用于过滤历史数据，YYYYMMDD 格式）
            
        Returns:
            Dict[str, Any]: 历史数据字典
                - klines: Dict[str, List[Dict]] - K线数据，key 是 term（"daily", "weekly", "monthly"）
                    {
                        "daily": [{"ts_code": "000001.SZ", "trade_date": "20250101", "close": 10.5, ...}, ...],
                        "weekly": [...],
                        "monthly": [...]
                    }
                - finance: List[Dict] - 财务数据（如果有）
                - ... 其他历史数据
        """
        historical_data = {}
        
        # 加载 kline 数据（根据 base_term 和 required_terms）
        kline_terms = set([self.base_term] + (self.required_terms or []))
        klines = {}
        
        for term in kline_terms:
            if self.data_source_mgr:
                # 从 data_source 系统加载
                kline_data = self.data_source_mgr.load_kline(
                    entity_id=entity_id,
                    term=term,
                    end_date=as_of_date
                )
                klines[term] = kline_data
            else:
                # 从数据库加载（备用方案）
                kline_model = self.data_mgr.get_model(f"stock_kline_{term}")
                if kline_model:
                    kline_data = kline_model.load_by_stock(entity_id, end_date=as_of_date)
                    klines[term] = kline_data
        
        historical_data["klines"] = klines
        
        # 加载其他数据源
        for data_source in self.required_data:
            if data_source == "corporate_finance":
                if self.data_source_mgr:
                    finance_data = self.data_source_mgr.load_corporate_finance(
                        entity_id=entity_id,
                        end_date=as_of_date
                    )
                    historical_data["finance"] = finance_data
                else:
                    finance_model = self.data_mgr.get_model("corporate_finance")
                    if finance_model:
                        finance_data = finance_model.load_by_stock(entity_id, end_date=as_of_date)
                        historical_data["finance"] = finance_data
        
        return historical_data
    
    # ========================================================================
    # 3. 迭代逻辑（根据 config 迭代，暴露钩子函数）
    # ========================================================================
    
    def calculate_for_entity(
        self,
        entity_id: str,
        entity_type: str = "stock",
        start_date: str = None,
        end_date: str = None
    ) -> List[TagEntity]:
        """
        为单个实体计算 tag（迭代逻辑）
        
        流程：
        1. 获取实体的时间范围（根据 update_mode）
        2. 根据 base_term 迭代每个时间点
        3. 在每个时间点调用 calculate_tag 钩子
        4. 收集所有 tag 并返回
        
        Args:
            entity_id: 实体ID（如股票代码）
            entity_type: 实体类型（默认 "stock"）
            start_date: 起始日期（YYYYMMDD，可选，用于增量计算）
            end_date: 结束日期（YYYYMMDD，可选，默认到最新）
            
        Returns:
            List[TagEntity]: 计算得到的 tag 列表
        """
        # 确定时间范围
        date_range = self._get_date_range(entity_id, entity_type, start_date, end_date)
        if not date_range:
            return []
        
        # 根据 base_term 获取迭代时间点列表
        iteration_dates = self._get_iteration_dates(date_range["start"], date_range["end"])
        
        # 加载完整历史数据（一次性加载，避免重复查询）
        historical_data = self.load_entity_data(
            entity_id=entity_id,
            entity_type=entity_type,
            as_of_date=date_range["end"]
        )
        
        # 迭代每个时间点
        tag_entities = []
        for as_of_date in iteration_dates:
            try:
                # 调用用户实现的 calculate_tag 钩子
                tag_entity = self.calculate_tag(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    as_of_date=as_of_date,
                    historical_data=historical_data
                )
                
                if tag_entity:
                    # 设置 tag_id 和 entity 信息
                    tag_entity.tag_id = self.tag_id  # 需要从数据库获取
                    tag_entity.entity_id = entity_id
                    tag_entity.entity_type = entity_type
                    tag_entities.append(tag_entity)
                    
                    # 调用 on_tag_created 钩子（可选）
                    self.on_tag_created(tag_entity, entity_id, as_of_date)
                    
            except Exception as e:
                # 调用错误处理钩子
                self.on_calculate_error(entity_id, as_of_date, e)
                # 根据配置决定是否继续或中断
                if self.should_continue_on_error():
                    continue
                else:
                    raise
        
        return tag_entities
    
    def _get_date_range(
        self,
        entity_id: str,
        entity_type: str,
        start_date: str = None,
        end_date: str = None
    ) -> Optional[Dict[str, str]]:
        """
        获取计算时间范围
        
        根据 update_mode 决定：
        - INCREMENTAL: 从最后计算时间 + 1 天开始
        - REFRESH: 从实体上市日期开始
        """
        if self.update_mode == UpdateMode.INCREMENTAL.value:
            # 增量计算：从最后计算时间 + 1 天开始
            if start_date:
                # 用户指定了起始日期
                calc_start = start_date
            else:
                # 查询最后计算时间
                last_date = self._get_last_calculated_date(entity_id, entity_type)
                if last_date:
                    # 从最后计算时间 + 1 天开始
                    calc_start = self._add_days(last_date, 1)
                else:
                    # 没有历史数据，从上市日期开始
                    calc_start = self._get_entity_listing_date(entity_id, entity_type)
        else:
            # 全量刷新：从上市日期开始
            calc_start = self._get_entity_listing_date(entity_id, entity_type)
        
        if not calc_start:
            return None
        
        # 结束日期
        calc_end = end_date or self._get_latest_date()
        
        if calc_start > calc_end:
            return None
        
        return {"start": calc_start, "end": calc_end}
    
    def _get_iteration_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        根据 base_term 获取迭代时间点列表
        
        例如：
        - base_term = "daily": 返回所有交易日
        - base_term = "weekly": 返回每周最后一个交易日
        - base_term = "monthly": 返回每月最后一个交易日
        """
        # TODO: 实现根据 base_term 获取时间点列表的逻辑
        # 需要调用 data_source 系统获取交易日历
        if self.data_source_mgr:
            return self.data_source_mgr.get_trade_dates(
                term=self.base_term,
                start_date=start_date,
                end_date=end_date
            )
        else:
            # 备用方案：从数据库获取
            # TODO: 实现
            return []
    
    # ========================================================================
    # 4. 计算钩子（用户实现）
    # ========================================================================
    
    @abstractmethod
    def calculate_tag(
        self, 
        entity_id: str,
        entity_type: str,
        as_of_date: str, 
        historical_data: Dict[str, Any]
    ) -> Optional[TagEntity]:
        """
        计算 tag（用户实现）
        
        钩子函数：在每个时间点调用，用户实现计算逻辑
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            entity_type: 实体类型（如 "stock", "kline_daily" 等）
            as_of_date: 当前时间点（YYYYMMDD 格式，如 "20250101"）
            historical_data: 完整历史数据（上帝视角）
                - klines: Dict[str, List[Dict]] - K线数据，key 是 term
                    {
                        "daily": [{"ts_code": "000001.SZ", "trade_date": "20250101", "close": 10.5, ...}, ...],
                        "weekly": [...],
                        "monthly": [...]
                    }
                - finance: List[Dict] - 财务数据（如果有）
                - ... 其他历史数据
        
        Returns:
            TagEntity 或 None（不创建 tag）
        """
        pass
    
    # ========================================================================
    # 5. 其他钩子函数（可选实现）
    # ========================================================================
    
    def on_init(self):
        """
        初始化钩子（可选实现）
        
        在 Calculator 初始化后调用，用于：
        - 初始化缓存
        - 预加载数据
        - 其他初始化操作
        """
        pass
    
    def on_tag_created(self, tag_entity: TagEntity, entity_id: str, as_of_date: str):
        """
        Tag 创建后钩子（可选实现）
        
        在 calculate_tag 返回 TagEntity 后调用，用于：
        - 记录日志
        - 更新缓存
        - 触发其他操作
        """
        pass
    
    def on_calculate_error(self, entity_id: str, as_of_date: str, error: Exception):
        """
        计算错误钩子（可选实现）
        
        在 calculate_tag 抛出异常时调用，用于：
        - 记录错误日志
        - 发送告警
        - 其他错误处理
        """
        # 默认实现：记录错误
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"计算 tag 失败: entity_id={entity_id}, as_of_date={as_of_date}, error={error}",
            exc_info=True
        )
    
    def should_continue_on_error(self) -> bool:
        """
        错误时是否继续（可选实现）
        
        返回 True 表示遇到错误时继续计算下一个时间点
        返回 False 表示遇到错误时中断计算
        
        默认：True（继续）
        """
        return True
    
    def on_finish(self, entity_id: str, tag_count: int):
        """
        完成钩子（可选实现）
        
        在单个实体计算完成后调用，用于：
        - 记录统计信息
        - 清理资源
        - 其他收尾操作
        """
        pass
    
    # ========================================================================
    # 6. 辅助方法
    # ========================================================================
    
    def create_tag(
        self, 
        value: str,
        as_of_date: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> TagEntity:
        """
        创建 Tag 实体（辅助方法）
        
        Args:
            value: 标签值（string）
            as_of_date: 业务日期（如果为 None，需要从上下文获取）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            TagEntity
        """
        return TagEntity(
            tag_id=self.tag_id,  # 需要从数据库获取
            entity_type="stock",  # 默认，实际使用时需要设置
            entity_id="",  # 需要从上下文设置
            value=value,
            as_of_date=as_of_date,
            start_date=start_date,
            end_date=end_date
        )
    
    # ========================================================================
    # 7. 多线程支持（由 TagExecutor 实现，Calculator 不需要关心）
    # ========================================================================
    # 多线程逻辑在 TagExecutor 中实现，Calculator 只负责单个实体的计算
```

## 🎯 使用示例

### 用户实现 Calculator

```python
from app.tag.base_calculator import BaseTagCalculator
from app.tag.entities import TagEntity
from typing import Optional, Dict, Any


class MomentumCalculator(BaseTagCalculator):
    """动量 Tag Calculator"""
    
    def calculate_tag(
        self, 
        entity_id: str,
        entity_type: str,
        as_of_date: str, 
        historical_data: Dict[str, Any]
    ) -> Optional[TagEntity]:
        """计算动量 tag"""
        # 获取 daily kline 数据
        daily_klines = historical_data.get("klines", {}).get("daily", [])
        
        if len(daily_klines) < 20:
            return None
        
        # 计算动量（示例）
        recent_close = daily_klines[-1]["close"]
        past_close = daily_klines[-20]["close"]
        momentum = (recent_close - past_close) / past_close
        
        # 创建 tag
        return self.create_tag(
            value=str(momentum),
            as_of_date=as_of_date
        )
    
    def on_init(self):
        """初始化：可以预加载一些数据"""
        # 例如：预加载股票列表
        pass
```

## 📝 设计说明

### 1. 配置管理
- ✅ 自动验证必需字段
- ✅ 处理默认值
- ✅ 验证枚举值
- ✅ 提取常用配置到实例变量

### 2. 数据加载
- ✅ 默认实现支持股票
- ✅ 可扩展支持其他 entity
- ✅ 支持加载多个 term 的 kline 数据

### 3. 迭代逻辑
- ✅ 根据 base_term 自动迭代
- ✅ 支持增量计算和全量刷新
- ✅ 一次性加载历史数据，避免重复查询

### 4. 钩子函数
- ✅ `calculate_tag`: 必需实现（计算逻辑）
- ✅ `on_init`: 可选（初始化）
- ✅ `on_tag_created`: 可选（tag 创建后）
- ✅ `on_calculate_error`: 可选（错误处理）
- ✅ `should_continue_on_error`: 可选（错误时是否继续）
- ✅ `on_finish`: 可选（完成时）

### 5. 多线程支持
- ✅ 多线程逻辑在 TagExecutor 中实现
- ✅ Calculator 只负责单个实体的计算
- ✅ 每个线程处理一个实体，避免内存爆炸

## 🔄 执行流程

```
1. 初始化 Calculator
   ├─ 加载 config
   ├─ 验证 config
   ├─ 处理默认值
   └─ 调用 on_init()

2. TagExecutor 启动多线程/多进程
   └─ 每个 worker 处理一个实体

3. 对每个实体：
   ├─ 调用 calculate_for_entity()
   │   ├─ 获取时间范围（根据 update_mode）
   │   ├─ 获取迭代时间点列表（根据 base_term）
   │   ├─ 加载历史数据（一次性加载）
   │   └─ 迭代每个时间点：
   │       ├─ 调用 calculate_tag() 钩子
   │       ├─ 如果返回 TagEntity，调用 on_tag_created()
   │       └─ 如果出错，调用 on_calculate_error()
   ├─ 保存所有 tag 到数据库
   └─ 调用 on_finish()

4. 所有实体计算完成
```

## ❓ 待讨论问题

1. **tag_id 如何获取？**
   - 方案1：在初始化时从数据库查询或创建
   - 方案2：在 TagExecutor 中设置
   - 建议：在 TagExecutor 中设置，Calculator 不需要关心

2. **历史数据加载时机？**
   - 方案1：每个时间点都加载（性能差）
   - 方案2：一次性加载完整历史数据（当前方案，性能好）
   - 建议：方案2，但需要确保内存不会爆炸

3. **错误处理策略？**
   - 方案1：遇到错误就中断（严格）
   - 方案2：遇到错误继续（宽松，当前默认）
   - 建议：提供配置选项，默认继续

4. **连续 tag 的处理？**
   - 方案1：在 calculate_tag 中处理（用户负责）
   - 方案2：在基类中自动处理（框架负责）
   - 建议：方案1，保持简单
