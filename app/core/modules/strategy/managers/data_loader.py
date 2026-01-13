#!/usr/bin/env python3
"""
Data Loader - 统一数据加载器

职责：
- 统一从 SOT 版本目录加载 opportunities 和 targets
- 支持按股票 ID 过滤
- 提供缓存机制（单策略缓存）
- 统一数据格式

设计原则：
- 使用实例方法（需要缓存状态）
- 单策略缓存：每个 DataLoader 实例只缓存一个策略的数据
- 缓存 key: f"{sot_version_dir.name}_{stock_id or 'all'}"
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import csv
import logging

from app.core.modules.strategy.models.event import Event

logger = logging.getLogger(__name__)


class DataLoader:
    """统一数据加载器（实例方法，支持缓存）"""
    
    def __init__(self, strategy_name: str, cache_enabled: bool = True):
        """
        初始化数据加载器
        
        Args:
            strategy_name: 策略名称（用于缓存标识）
            cache_enabled: 是否启用缓存
        """
        self.strategy_name = strategy_name
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}  # 缓存当前策略的数据
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.debug(f"[DataLoader] 已清空缓存: strategy={self.strategy_name}")
    
    # =========================================================================
    # 机会和目标数据加载
    # =========================================================================
    
    def load_opportunities(
        self,
        sot_version_dir: Path,
        stock_id: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict[str, Any]]:
        """
        加载机会数据
        
        Args:
            sot_version_dir: SOT 版本目录
            stock_id: 股票 ID（可选，如果指定则只加载该股票的数据）
            start_date: 开始日期过滤（YYYYMMDD，可选）
            end_date: 结束日期过滤（YYYYMMDD，可选）
        
        Returns:
            机会列表
        """
        if stock_id:
            # 加载单个股票的机会
            opportunities_path = sot_version_dir / f"{stock_id}_opportunities.csv"
            if not opportunities_path.exists():
                logger.warning(
                    f"[DataLoader] opportunities 文件不存在: {opportunities_path}"
                )
                return []
            
            opportunities = self._load_opportunities_from_file(
                opportunities_path, start_date, end_date
            )
            return opportunities
        else:
            # 加载所有股票的机会
            opportunities: List[Dict[str, Any]] = []
            for entry in sot_version_dir.iterdir():
                if not entry.is_file():
                    continue
                
                if entry.name.endswith("_opportunities.csv"):
                    stock_opps = self._load_opportunities_from_file(
                        entry, start_date, end_date
                    )
                    opportunities.extend(stock_opps)
            
            return opportunities
    
    def load_targets(
        self,
        sot_version_dir: Path,
        stock_id: Optional[str] = None,
        opportunity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        加载目标数据
        
        Args:
            sot_version_dir: SOT 版本目录
            stock_id: 股票 ID（可选，如果指定则只加载该股票的数据）
            opportunity_id: 机会 ID（可选，如果指定则只加载该机会的目标）
        
        Returns:
            目标列表
        """
        if stock_id:
            # 加载单个股票的目标
            targets_path = sot_version_dir / f"{stock_id}_targets.csv"
            if not targets_path.exists():
                return []
            
            targets = self._load_targets_from_file(targets_path, opportunity_id)
            return targets
        else:
            # 加载所有股票的目标
            targets: List[Dict[str, Any]] = []
            for entry in sot_version_dir.iterdir():
                if not entry.is_file():
                    continue
                
                if entry.name.endswith("_targets.csv"):
                    stock_targets = self._load_targets_from_file(entry, opportunity_id)
                    targets.extend(stock_targets)
            
            return targets
    
    def load_opportunities_and_targets(
        self,
        sot_version_dir: Path,
        stock_id: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        加载机会和目标数据（带缓存）
        
        缓存策略：
        - 缓存 key: f"{sot_version_dir.name}_{stock_id or 'all'}"
        - 只缓存当前策略的数据
        - 切换策略时需要创建新的 DataLoader 实例
        
        Args:
            sot_version_dir: SOT 版本目录
            stock_id: 股票 ID（可选）
            start_date: 开始日期过滤（YYYYMMDD，可选）
            end_date: 结束日期过滤（YYYYMMDD，可选）
        
        Returns:
            (opportunities, targets_map):
                - opportunities: 过滤后的机会列表
                - targets_map: 按 opportunity_id 分组的 targets 字典
        """
        # 构建缓存 key
        cache_key = f"{sot_version_dir.name}_{stock_id or 'all'}_{start_date}_{end_date}"
        
        # 检查缓存
        if self.cache_enabled and cache_key in self._cache:
            logger.debug(
                f"[DataLoader] 使用缓存: strategy={self.strategy_name}, "
                f"key={cache_key}"
            )
            return self._cache[cache_key]
        
        # 加载数据
        if stock_id:
            # 加载单个股票的数据
            opportunities_path = sot_version_dir / f"{stock_id}_opportunities.csv"
            targets_path = sot_version_dir / f"{stock_id}_targets.csv"
            
            opportunities, targets_map = self._load_from_files(
                opportunities_path, targets_path, start_date, end_date
            )
        else:
            # 加载所有股票的数据
            opportunities: List[Dict[str, Any]] = []
            targets_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            
            for entry in sot_version_dir.iterdir():
                if not entry.is_file():
                    continue
                
                if entry.name.endswith("_opportunities.csv"):
                    stock_id_from_file = entry.name[: -len("_opportunities.csv")]
                    targets_path = sot_version_dir / f"{stock_id_from_file}_targets.csv"
                    
                    stock_opps, stock_targets_map = self._load_from_files(
                        entry, targets_path, start_date, end_date
                    )
                    opportunities.extend(stock_opps)
                    targets_map.update(stock_targets_map)
        
        result = (opportunities, targets_map)
        
        # 更新缓存
        if self.cache_enabled:
            self._cache[cache_key] = result
            logger.debug(
                f"[DataLoader] 已缓存: strategy={self.strategy_name}, "
                f"key={cache_key}, opportunities={len(opportunities)}"
            )
        
        return result
    
    def build_event_stream(
        self,
        sot_version_dir: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Event]:
        """
        从 SOT 目录构建全局事件流
        
        Args:
            sot_version_dir: SOT 版本目录
            start_date: 开始日期过滤（YYYYMMDD，可选）
            end_date: 结束日期过滤（YYYYMMDD，可选）
        
        Returns:
            事件列表，按日期排序
        """
        events: List[Event] = []
        
        # 扫描所有 opportunities 和 targets 文件
        for entry in sot_version_dir.iterdir():
            if not entry.is_file():
                continue
            
            name = entry.name
            if name.endswith("_opportunities.csv"):
                stock_id = name[: -len("_opportunities.csv")]
                targets_path = sot_version_dir / f"{stock_id}_targets.csv"
                
                # 加载机会和目标
                opportunities, targets_map = self.load_opportunities_and_targets(
                    sot_version_dir,
                    stock_id=stock_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                
                # 为每个机会创建 trigger 事件
                for opp in opportunities:
                    opp_id = str(opp.get("opportunity_id") or "").strip()
                    trigger_date = opp.get("trigger_date") or ""
                    
                    if not opp_id or not trigger_date:
                        continue
                    
                    events.append(Event(
                        event_type="trigger",
                        date=trigger_date,
                        stock_id=stock_id,
                        opportunity_id=opp_id,
                        opportunity=opp,
                        target=None,
                    ))
                    
                    # 为该机会的所有 targets 创建 target 事件
                    targets = targets_map.get(opp_id, [])
                    for target in targets:
                        target_date = target.get("date") or ""
                        if not target_date:
                            continue
                        
                        events.append(Event(
                            event_type="target",
                            date=target_date,
                            stock_id=stock_id,
                            opportunity_id=opp_id,
                            opportunity=opp,  # 包含完整的 opportunity 信息
                            target=target,
                        ))
        
        # 按日期排序，同日多事件按 (stock_id, opportunity_id, event_type) 排序
        events.sort(key=lambda e: (
            e.date,
            e.stock_id,
            e.opportunity_id,
            e.event_type,
        ))
        
        logger.info(
            f"[DataLoader] 构建事件流: 共 {len(events)} 个事件 "
            f"(trigger={sum(1 for e in events if e.is_trigger())}, "
            f"target={sum(1 for e in events if e.is_target())})"
        )
        
        return events
    
    # =========================================================================
    # 私有辅助方法
    # =========================================================================
    
    def _load_from_files(
        self,
        opportunities_path: Path,
        targets_path: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        从文件加载机会和目标数据
        
        Args:
            opportunities_path: opportunities CSV 文件路径
            targets_path: targets CSV 文件路径
            start_date: 开始日期过滤（YYYYMMDD，可选）
            end_date: 结束日期过滤（YYYYMMDD，可选）
        
        Returns:
            (opportunities, targets_map)
        """
        # 1. 读取 targets，按 opportunity_id 分组
        targets_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        if targets_path.exists():
            with targets_path.open("r", encoding="utf-8") as f_t:
                t_reader = csv.DictReader(f_t)
                for row in t_reader:
                    opp_id = str(row.get("opportunity_id") or "").strip()
                    if not opp_id:
                        continue
                    # 规范化数值字段
                    try:
                        row["weighted_profit"] = float(row.get("weighted_profit") or 0.0)
                    except (ValueError, TypeError):
                        row["weighted_profit"] = 0.0
                    targets_map[opp_id].append(row)
        
        # 2. 读取所有机会
        opportunities: List[Dict[str, Any]] = []
        if not opportunities_path.exists():
            logger.warning(
                f"[DataLoader] opportunities 文件不存在: {opportunities_path}"
            )
            return opportunities, targets_map
        
        with opportunities_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trigger_date = row.get("trigger_date") or ""
                
                # 时间窗口过滤（基于字符串比较，YYYYMMDD 形式）
                if start_date and trigger_date < start_date:
                    continue
                if end_date and trigger_date > end_date:
                    continue
                
                opportunities.append(row)
        
        return opportunities, targets_map
    
    def _load_opportunities_from_file(
        self,
        opportunities_path: Path,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict[str, Any]]:
        """从文件加载机会数据"""
        opportunities: List[Dict[str, Any]] = []
        
        if not opportunities_path.exists():
            return opportunities
        
        with opportunities_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trigger_date = row.get("trigger_date") or ""
                
                # 时间窗口过滤
                if start_date and trigger_date < start_date:
                    continue
                if end_date and trigger_date > end_date:
                    continue
                
                opportunities.append(row)
        
        return opportunities
    
    def _load_targets_from_file(
        self,
        targets_path: Path,
        opportunity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """从文件加载目标数据"""
        targets: List[Dict[str, Any]] = []
        
        if not targets_path.exists():
            return targets
        
        with targets_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 如果指定了 opportunity_id，只加载匹配的目标
                if opportunity_id:
                    opp_id = str(row.get("opportunity_id") or "").strip()
                    if opp_id != opportunity_id:
                        continue
                
                # 规范化数值字段
                try:
                    row["weighted_profit"] = float(row.get("weighted_profit") or 0.0)
                except (ValueError, TypeError):
                    row["weighted_profit"] = 0.0
                
                targets.append(row)
        
        return targets
