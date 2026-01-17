#!/usr/bin/env python3
"""
Opportunity Service - 机会数据服务

职责：
- 管理 Opportunity 的 JSON 文件存储
- 保存扫描结果（scan）
- 保存模拟结果（simulate）
- 加载历史机会
- 生成 Summary
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import logging

from core.infra.project_context import PathManager
from core.modules.strategy.enums import OpportunityStatus

logger = logging.getLogger(__name__)


class OpportunityService:
    """Opportunity 数据服务（JSON 存储）"""
    
    def __init__(self, strategy_name: str):
        """
        初始化服务
        
        Args:
            strategy_name: 策略名称
        """
        self.strategy_name = strategy_name
        
        # 结果文件夹路径
        self.base_path = PathManager.strategy_results(strategy_name)
        self.scan_path = self.base_path / "scan"
        self.simulate_path = self.base_path / "simulate"
        
        # 确保文件夹存在
        self.scan_path.mkdir(parents=True, exist_ok=True)
        self.simulate_path.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # Scanner 相关
    # =========================================================================
    
    def save_scan_opportunities(
        self, 
        date: str, 
        stock_id: str, 
        opportunities: List[Dict[str, Any]]
    ):
        """
        保存扫描结果
        
        文件路径：scan/{date}/{stock_id}.json
        
        Args:
            date: 扫描日期（如 20251219）
            stock_id: 股票代码
            opportunities: 机会列表
        
        文件格式：
        {
            "stock": {"id": "000001.SZ", "name": "平安银行"},
            "opportunities": [...],
            "summary": {...}
        }
        """
        # 1. 创建日期文件夹
        date_folder = self.scan_path / date
        date_folder.mkdir(parents=True, exist_ok=True)
        
        # 2. 读取现有数据（如果存在）
        file_path = date_folder / f"{stock_id}.json"
        
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # 获取股票名称
            stock_name = opportunities[0].get('stock_name', '') if opportunities else ''
            data = {
                "stock": {"id": stock_id, "name": stock_name},
                "opportunities": [],
                "summary": {}
            }
        
        # 3. 添加新机会（去重）
        existing_ids = {o['opportunity_id'] for o in data['opportunities']}
        for opp in opportunities:
            if opp['opportunity_id'] not in existing_ids:
                data['opportunities'].append(opp)
        
        # 4. 计算 summary
        data['summary'] = self._calculate_summary(data['opportunities'])
        
        # 5. 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 6. 更新 latest 软链接
        self._update_latest_link(self.scan_path, date)
    
    def load_scan_opportunities(self, date: str = None) -> List[Dict[str, Any]]:
        """
        加载扫描结果
        
        Args:
            date: 扫描日期（如 20251219，默认 latest）
        
        Returns:
            opportunities: [
                {'opportunity_id': '...', 'stock_id': '...', ...},
                ...
            ]
        """
        # 1. 确定加载哪个日期
        if date is None:
            # 加载最新
            latest_link = self.scan_path / "latest"
            if not latest_link.exists():
                logger.warning("没有找到扫描结果")
                return []
            date = latest_link.resolve().name
        
        # 2. 读取所有股票文件
        date_folder = self.scan_path / date
        if not date_folder.exists():
            logger.warning(f"扫描日期不存在: {date}")
            return []
        
        opportunities = []
        for file_path in date_folder.glob("*.json"):
            if file_path.name == "summary.json":
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取所有机会
            for opp in data.get('opportunities', []):
                opportunities.append(opp)
        
        return opportunities
    
    def save_scan_summary(self, date: str, summary: Dict[str, Any]):
        """
        保存扫描汇总
        
        文件路径：scan/{date}/summary.json
        """
        date_folder = self.scan_path / date
        date_folder.mkdir(parents=True, exist_ok=True)
        
        summary_file = date_folder / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def save_scan_config(self, date: str, config: Dict[str, Any]):
        """
        保存扫描配置
        
        文件路径：scan/{date}/config.json
        """
        date_folder = self.scan_path / date
        date_folder.mkdir(parents=True, exist_ok=True)
        
        config_file = date_folder / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    # =========================================================================
    # Simulator 相关
    # =========================================================================
    
    def save_simulate_opportunities(
        self,
        session_id: str,
        stock_id: str,
        opportunities: List[Dict[str, Any]]
    ):
        """
        保存模拟结果
        
        文件路径：simulate/{session_id}/{stock_id}.json
        
        Args:
            session_id: Session ID（如 session_001）
            stock_id: 股票代码
            opportunities: 回测后的机会列表
        """
        # 1. 创建 session 文件夹
        session_folder = self.simulate_path / session_id
        session_folder.mkdir(parents=True, exist_ok=True)
        
        # 2. 构建数据
        stock_name = opportunities[0].get('stock_name', '') if opportunities else ''
        data = {
            "stock": {"id": stock_id, "name": stock_name},
            "opportunities": opportunities,
            "summary": self._calculate_summary(opportunities)
        }
        
        # 3. 保存文件
        file_path = session_folder / f"{stock_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 4. 更新 latest 软链接
        self._update_latest_link(self.simulate_path, session_id)
    
    def save_simulate_summary(self, session_id: str, summary: Dict[str, Any]):
        """
        保存模拟汇总
        
        文件路径：simulate/{session_id}/summary.json
        """
        session_folder = self.simulate_path / session_id
        session_folder.mkdir(parents=True, exist_ok=True)
        
        summary_file = session_folder / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def save_simulate_config(self, session_id: str, config: Dict[str, Any]):
        """
        保存模拟配置
        
        文件路径：simulate/{session_id}/config.json
        """
        session_folder = self.simulate_path / session_id
        session_folder.mkdir(parents=True, exist_ok=True)
        
        config_file = session_folder / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    # =========================================================================
    # 辅助方法
    # =========================================================================
    
    def _calculate_summary(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算机会汇总统计
        
        Args:
            opportunities: 机会列表
        
        Returns:
            summary: {
                'total_opportunities': 10,
                'total_closed': 8,
                'win_rate': 0.65,
                'avg_price_return': 0.05,
                ...
            }
        """
        if not opportunities:
            return {}
        
        closed_opps = [o for o in opportunities if o.get('status') == OpportunityStatus.CLOSED.value]
        
        summary = {
            'total_opportunities': len(opportunities),
            'total_closed': len(closed_opps)
        }
        
        if closed_opps:
            # 胜率
            wins = sum(1 for o in closed_opps if o.get('price_return', 0) > 0)
            summary['win_rate'] = wins / len(closed_opps)
            
            # 平均收益率
            summary['avg_price_return'] = sum(o.get('price_return', 0) for o in closed_opps) / len(closed_opps)
            
            # 平均持有天数
            summary['avg_holding_days'] = sum(o.get('holding_days', 0) for o in closed_opps) / len(closed_opps)
            
            # 年化收益率（假设 250 个交易日）
            if summary['avg_holding_days'] > 0:
                summary['annual_return'] = summary['avg_price_return'] * (250 / summary['avg_holding_days'])
        
        return summary
    
    def _update_latest_link(self, base_path: Path, target: str):
        """
        更新 latest 软链接
        
        Args:
            base_path: 基础路径（scan_path 或 simulate_path）
            target: 目标文件夹名（日期或 session_id）
        """
        latest_link = base_path / "latest"
        
        # 删除旧链接
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        
        # 创建新链接
        try:
            latest_link.symlink_to(target, target_is_directory=True)
        except Exception as e:
            logger.warning(f"创建软链接失败: {e}")
