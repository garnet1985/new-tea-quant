#!/usr/bin/env python3
"""
ScanCacheManager - 扫描结果缓存管理器

职责：
- 保存扫描结果到 CSV
- 加载历史缓存
- 清理过期缓存（最多保留 N 个交易日）
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import csv
import logging
from datetime import datetime

from app.core.modules.strategy.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class ScanCacheManager:
    """扫描结果缓存管理器"""
    
    strategy_name: str
    max_cache_days: int = 10
    
    def __post_init__(self):
        """初始化缓存目录"""
        self.cache_base_dir = Path(
            f"app/userspace/strategies/{self.strategy_name}/scan_cache"
        )
        self.cache_base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_opportunities(
        self,
        date: str,
        opportunities: List[Opportunity]
    ) -> None:
        """
        保存扫描结果到 CSV
        
        Args:
            date: 扫描日期（YYYYMMDD）
            opportunities: 机会列表
        """
        if not opportunities:
            logger.warning(f"[ScanCacheManager] 日期 {date} 没有机会，跳过保存")
            return
        
        # 创建日期目录
        date_dir = self.cache_base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # CSV 文件路径
        csv_path = date_dir / "opportunities.csv"
        
        # 转换为字典列表
        rows = []
        for opp in opportunities:
            row = opp.to_dict()
            # 确保所有值都是可序列化的
            for key, value in row.items():
                if value is None:
                    row[key] = ''
                elif isinstance(value, dict):
                    import json
                    row[key] = json.dumps(value, ensure_ascii=False)
                elif not isinstance(value, (str, int, float, bool)):
                    row[key] = str(value)
            rows.append(row)
        
        # 写入 CSV
        if rows:
            fieldnames = sorted({k for row in rows for k in row.keys()})
            with csv_path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(
                f"[ScanCacheManager] 已保存 {len(opportunities)} 个机会到 {csv_path}"
            )
    
    def load_opportunities(
        self,
        date: str
    ) -> List[Opportunity]:
        """
        加载历史缓存
        
        Args:
            date: 扫描日期（YYYYMMDD）
        
        Returns:
            机会列表（如果不存在返回空列表）
        """
        csv_path = self.cache_base_dir / date / "opportunities.csv"
        
        if not csv_path.exists():
            return []
        
        opportunities = []
        try:
            with csv_path.open('r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 转换回 Opportunity
                    # 处理 JSON 字符串字段
                    for key, value in row.items():
                        if value and value.startswith('{'):
                            try:
                                import json
                                row[key] = json.loads(value)
                            except:
                                pass
                    
                    # 从字典创建 Opportunity
                    opp = Opportunity.from_dict(row)
                    opportunities.append(opp)
            
            logger.info(
                f"[ScanCacheManager] 从缓存加载 {len(opportunities)} 个机会: {date}"
            )
            
        except Exception as e:
            logger.warning(f"[ScanCacheManager] 加载缓存失败: {date}, error={e}")
        
        return opportunities
    
    def cleanup_old_cache(self) -> None:
        """
        清理过期缓存（保留最多 max_cache_days 个交易日）
        
        逻辑：
        1. 列出所有日期目录
        2. 按日期排序（最新的在前）
        3. 删除超过 max_cache_days 的旧目录
        """
        if not self.cache_base_dir.exists():
            return
        
        # 获取所有日期目录
        date_dirs = [
            d for d in self.cache_base_dir.iterdir()
            if d.is_dir() and d.name.isdigit() and len(d.name) == 8
        ]
        
        if len(date_dirs) <= self.max_cache_days:
            return
        
        # 按日期排序（最新的在前）
        date_dirs.sort(key=lambda d: d.name, reverse=True)
        
        # 删除超过 max_cache_days 的旧目录
        to_delete = date_dirs[self.max_cache_days:]
        for date_dir in to_delete:
            try:
                import shutil
                shutil.rmtree(date_dir)
                logger.info(f"[ScanCacheManager] 已删除过期缓存: {date_dir.name}")
            except Exception as e:
                logger.warning(f"[ScanCacheManager] 删除缓存失败: {date_dir.name}, error={e}")
