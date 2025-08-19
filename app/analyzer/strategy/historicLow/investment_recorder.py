#!/usr/bin/env python3
"""
投资记录器 - 记录投资结算信息
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger
from .strategy_settings import invest_settings
# 导入策略设置
class InvestmentRecorder:
    """投资记录器 - 记录投资结算信息"""
    
    def __init__(self, base_dir: str = "tmp"):
        """
        初始化投资记录器
        
        Args:
            base_dir: 基础目录路径
        """
        self.tmp_dir = base_dir
        self.current_session_dir = None
        self.meta_file = os.path.join(base_dir, "meta.json")
        
        # 确保基础目录存在
        os.makedirs(base_dir, exist_ok=True)
        
        # 创建新的会话目录
        self._create_new_session()
    
    def _create_new_session(self):
        """创建新的会话目录"""
        # 获取当前日期
        current_date = datetime.now().strftime("%Y_%m_%d")
        
        # 从meta.json获取下一个ID
        next_id = self._get_next_session_id()
        
        # 创建会话名称
        session_name = f"{current_date}-{next_id:03d}"
        self.current_session_dir = os.path.join(self.tmp_dir, session_name)
        
        # 创建会话目录
        os.makedirs(self.current_session_dir, exist_ok=True)
        
        # 更新meta.json
        self._update_meta_file(next_id, session_name)
        
        logger.info(f"📁 创建新的投资记录会话: {session_name}")
        
        # 创建会话信息文件
        session_info = {
            "session_id": next_id,
            "session_name": session_name,
            "created_at": datetime.now().isoformat(),
            "date": current_date,
            "description": "HistoricLow策略投资记录会话",
            "total_stocks_tested": 0,
            "investment_summary": {
                "total_investment_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "open_count": 0,
                "win_rate": 0.0,
                "annual_return": 0.0,
                "avg_duration_days": 0.0,
                "avg_roi": 0.0,
                "total_investments": 0,
                "win_count": 0,
                "loss_count": 0
            },
            "strategy_settings": {
                "goal": invest_settings["goal"]
            }
        }
        
        session_info_file = os.path.join(self.current_session_dir, "session_info.json")
        with open(session_info_file, "w", encoding="utf-8") as f:
            json.dump(session_info, f, ensure_ascii=False, indent=2)
    
    def _get_next_session_id(self) -> int:
        """从meta.json获取下一个会话ID"""
        if not os.path.exists(self.meta_file):
            # 如果meta.json不存在，创建初始文件
            initial_meta = {
                "current_max_id": 0,
                "last_updated": datetime.now().isoformat(),
                "sessions": []
            }
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(initial_meta, f, ensure_ascii=False, indent=2)
            return 1
        
        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("current_max_id", 0) + 1
        except Exception as e:
            logger.error(f"❌ 读取meta.json失败: {e}")
            return 1
    
    def _update_meta_file(self, session_id: int, session_name: str):
        """更新meta.json文件"""
        try:
            if os.path.exists(self.meta_file):
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                meta = {
                    "current_max_id": 0,
                    "last_updated": datetime.now().isoformat(),
                    "sessions": []
                }
            
            # 更新最大ID
            meta["current_max_id"] = max(meta.get("current_max_id", 0), session_id)
            meta["last_updated"] = datetime.now().isoformat()
            
            # 添加新会话信息
            session_info = {
                "id": session_id,
                "name": session_name,
                "created_at": datetime.now().isoformat(),
                "path": self.current_session_dir
            }
            meta["sessions"].append(session_info)
            
            # 保存更新后的meta.json
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ 更新meta.json失败: {e}")
    
    def _convert_decimal(self, value):
        """转换Decimal类型为float，处理JSON序列化问题"""
        if value is None:
            return None
        try:
            # 如果是Decimal类型，转换为float
            if hasattr(value, '__float__'):
                return float(value)
            # 如果是字符串，尝试转换为float
            elif isinstance(value, str):
                return float(value)
            # 其他类型直接返回
            else:
                return value
        except (ValueError, TypeError):
            return value
    
    def record_investment(self, stock_info: Dict[str, Any], investment_data: Dict[str, Any], status: str):
        """
        记录投资信息
        
        Args:
            stock_info: 股票基本信息
            investment_data: 投资数据
            status: 投资状态 (success/fail/open)
        """
        if not self.current_session_dir:
            logger.warning("当前没有活跃的会话")
            return
        
        # 创建股票投资记录文件
        stock_id = stock_info.get('code', 'unknown')
        stock_file_path = os.path.join(self.current_session_dir, f"{stock_id}.json")
        
        # 读取现有文件或创建新文件
        stock_data = self._load_stock_data(stock_file_path, stock_info)
        
        # 添加新的投资记录
        investment_record = {
            'investment_info': investment_data.get('investment_info', {}),
            'settlement_info': investment_data.get('settlement_info', {}),
            'status': status,
            'recorded_at': datetime.now().isoformat()
        }
        
        stock_data['results'].append(investment_record)
        
        # 更新统计信息
        self._update_stock_statistics(stock_data)
        
        # 保存文件
        self._save_stock_data(stock_file_path, stock_data)
        
        logger.info(f"📝 记录 {stock_id} 的 {status} 投资: {investment_record['investment_info'].get('start_date', 'unknown')}")

    def _load_stock_data(self, file_path: str, stock_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        加载股票数据文件，如果不存在则创建新的
        
        Args:
            file_path: 文件路径
            stock_info: 股票基本信息
            
        Returns:
            dict: 股票数据
        """
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
        
        # 创建新的股票数据结构
        return {
            'stock_info': {
                'code': stock_info.get('code', ''),
                'name': stock_info.get('name', ''),
                'market': stock_info.get('market', ''),
                'sector': stock_info.get('sector', ''),
                'industry': stock_info.get('industry', '')
            },
            'session_info': {
                'session_id': self.current_session_id,
                'created_at': datetime.now().isoformat(),
                'strategy': 'HistoricLow'
            },
            'results': [],
            'statistics': {
                'total_investments': 0,
                'success_count': 0,
                'fail_count': 0,
                'open_count': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'avg_profit': 0.0,
                'avg_duration_days': 0.0
            }
        }

    def _update_stock_statistics(self, stock_data: Dict[str, Any]):
        """
        更新股票统计信息
        
        Args:
            stock_data: 股票数据
        """
        results = stock_data['results']
        stats = stock_data['statistics']
        
        stats['total_investments'] = len(results)
        stats['success_count'] = len([r for r in results if r['status'] == 'success'])
        stats['fail_count'] = len([r for r in results if r['status'] == 'fail'])
        stats['open_count'] = len([r for r in results if r['status'] == 'open'])
        
        if stats['total_investments'] > 0:
            stats['win_rate'] = (stats['success_count'] / stats['total_investments']) * 100
        
        # 计算利润统计
        total_profit = 0.0
        total_duration = 0
        settled_count = 0
        
        for result in results:
            if result['status'] in ['success', 'fail']:
                profit = result['settlement_info'].get('profit_loss', 0)
                total_profit += profit
                duration = result['settlement_info'].get('duration_days', 0)
                total_duration += duration
                settled_count += 1
        
        stats['total_profit'] = total_profit
        if settled_count > 0:
            stats['avg_profit'] = total_profit / settled_count
            stats['avg_duration_days'] = total_duration / settled_count

    def _save_stock_data(self, file_path: str, stock_data: Dict[str, Any]):
        """
        保存股票数据到文件
        
        Args:
            file_path: 文件路径
            stock_data: 股票数据
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stock_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")

    def get_stock_results(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定股票的投资结果
        
        Args:
            stock_id: 股票ID
            
        Returns:
            dict: 股票投资结果，如果不存在返回None
        """
        if not self.current_session_dir:
            return None
        
        stock_file_path = os.path.join(self.current_session_dir, f"{stock_id}.json")
        if os.path.exists(stock_file_path):
            try:
                with open(stock_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"读取股票结果失败 {stock_file_path}: {e}")
        
        return None
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取当前会话信息"""
        return {
            "session_dir": self.current_session_dir,
            "created_at": datetime.now().isoformat()
        }
    
    def update_session_summary(self, summary_data: Dict[str, Any]) -> None:
        """
        更新会话信息文件中的投资摘要
        
        Args:
            summary_data: 投资摘要数据
        """
        try:
            session_info_file = os.path.join(self.current_session_dir, "session_info.json")
            
            if os.path.exists(session_info_file):
                with open(session_info_file, "r", encoding="utf-8") as f:
                    session_info = json.load(f)
            else:
                session_info = {}
            
            # 更新投资摘要信息
            session_info["investment_summary"] = summary_data
            session_info["last_updated"] = datetime.now().isoformat()
            
            # 写回文件
            with open(session_info_file, "w", encoding="utf-8") as f:
                json.dump(session_info, f, ensure_ascii=False, indent=2)
                
            logger.info(f"📝 已更新会话摘要信息: {self.current_session_dir}")
            
        except Exception as e:
            logger.error(f"❌ 更新会话摘要失败: {e}")

    def update_session_info(self, update_data: Dict[str, Any]) -> None:
        """
        更新会话信息文件中的外层字段
        
        Args:
            update_data: 要更新的字段数据
        """
        try:
            session_info_file = os.path.join(self.current_session_dir, "session_info.json")
            
            if os.path.exists(session_info_file):
                with open(session_info_file, "r", encoding="utf-8") as f:
                    session_info = json.load(f)
            else:
                session_info = {}
            
            # 更新外层字段
            session_info.update(update_data)
            session_info["last_updated"] = datetime.now().isoformat()
            
            # 写回文件
            with open(session_info_file, "w", encoding="utf-8") as f:
                json.dump(session_info, f, ensure_ascii=False, indent=2)
                
            logger.info(f"📝 已更新会话信息: {self.current_session_dir}")
            
        except Exception as e:
            logger.error(f"❌ 更新会话信息失败: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取投资记录摘要"""
        if not self.current_session_dir:
            return {}
        
        # 统计各个子目录下的投资记录数量
        success_count = len([f for f in os.listdir(os.path.join(self.current_session_dir, "success")) if f.endswith('.json')]) if os.path.exists(os.path.join(self.current_session_dir, "success")) else 0
        fail_count = len([f for f in os.listdir(os.path.join(self.current_session_dir, "fail")) if f.endswith('.json')]) if os.path.exists(os.path.join(self.current_session_dir, "fail")) else 0
        open_count = len([f for f in os.listdir(os.path.join(self.current_session_dir, "open")) if f.endswith('.json')]) if os.path.exists(os.path.join(self.current_session_dir, "open")) else 0
        
        total_count = success_count + fail_count + open_count
        
        return {
            "session_dir": self.current_session_dir,
            "total_investment_count": total_count,
            "success_count": success_count,
            "fail_count": fail_count,
            "open_count": open_count,
            "created_at": datetime.now().isoformat()
        }
