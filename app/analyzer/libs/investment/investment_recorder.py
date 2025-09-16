#!/usr/bin/env python3
"""
投资记录器 - 记录投资结算信息，支持基于策略和会话ID的存储管理
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger


class InvestmentRecorder:
    """投资记录器 - 记录投资结算信息，支持基于策略和会话ID的存储管理"""
    
    def __init__(self, strategy_name: str, session_id: Optional[str] = None):
        """
        初始化投资记录器
        
        Args:
            strategy_name: 策略名称，用于确定存储路径
            session_id: 会话ID，如果为None则自动生成
        """
        self.strategy_name = strategy_name
        
        # 设置tmp目录路径（在策略目录下）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 向上找到项目根目录，然后找到对应策略的tmp目录
        # 从 app/analyzer/libs/investment/ 向上到项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        strategy_dir = os.path.join(project_root, "app", "analyzer", "strategy", strategy_name)
        self.tmp_dir = os.path.join(strategy_dir, "tmp")
        self.meta_file = os.path.join(self.tmp_dir, "meta.json")
        
        # 确保tmp目录存在
        os.makedirs(self.tmp_dir, exist_ok=True)
        
        # 初始化meta.json文件
        self._init_meta_file()
        
        # 获取当前会话ID
        self.current_session_id = session_id or self._get_next_session_id()

    def _init_meta_file(self):
        """初始化meta.json文件"""
        if not os.path.exists(self.meta_file):
            meta = {
                "next_session_id": 1,
                "last_updated": datetime.now().isoformat(),
                "strategy_name": self.strategy_name
            }
            with open(self.meta_file, "w", encoding="utf-8") as file:
                json.dump(meta, file, ensure_ascii=False, indent=2)
        
    # ========================================================
    # stock summary:
    # ========================================================

    def save_stock_summary(self, stock_summary: Dict[str, Any]) -> None:
        """保存股票汇总信息到文件"""
        
        # 获取当前session目录
        session_dir = self._get_session_dir()
        os.makedirs(session_dir, exist_ok=True)
        
        # 生成文件名
        stock_id = stock_summary['stock_info']['id']
        file_path = os.path.join(session_dir, f"{stock_id}.json")
        
        # 保存到文件
        self._save_json_to_file(stock_summary, file_path)

    # ========================================================
    # session summary:
    # ========================================================

    def save_session(self, session_summary: Dict[str, Any]):
        """生成会话汇总"""
        # 保存会话汇总
        session_dir = self._get_session_dir()
        os.makedirs(session_dir, exist_ok=True)
        summary_file = os.path.join(session_dir, "session_summary.json")
        
        self._save_json_to_file(session_summary, summary_file)

        logger.info(f"📝 会话汇总已保存: {summary_file}")
        
        # 更新meta文件
        self._update_meta_file()
        
        return session_summary

    def _get_session_dir(self):
        """获取当前会话目录路径"""
        session_name = f"{datetime.now().strftime('%Y_%m_%d')}-{self.current_session_id}"
        return os.path.join(self.tmp_dir, session_name)

    def _get_next_session_id(self):
        """获取下一个会话ID"""
        with open(self.meta_file, "r", encoding="utf-8") as file:
            meta = json.load(file)
        return meta.get("next_session_id", 1)

    # ========================================================
    # Meta:
    # ========================================================

    def _update_meta_file(self):
        """更新meta.json文件"""
        meta = {
            "next_session_id": self.current_session_id + 1,
            "last_updated": datetime.now().isoformat(),
            "strategy_name": self.strategy_name
        }
        with open(self.meta_file, "w", encoding="utf-8") as file:
            json.dump(meta, file, ensure_ascii=False, indent=2)
    
    # ========================================================
    # Data retrieval:
    # ========================================================
    
    def get_stock_summary(self, stock_id: str, ref_version: str = None) -> Optional[Dict[str, Any]]:
        """
        获取指定股票的模拟结果summary
        
        Args:
            stock_id: 股票ID
            ref_version: 参考版本号，如果为None则使用默认版本
            
        Returns:
            Dict[str, Any]: 股票的summary信息，如果不存在则返回None
        """
        # 获取参考版本号
        if ref_version is None:
            ref_version = "524"  # 默认参考版本
        
        # 构建参考结果目录路径
        ref_dir = os.path.join(self.tmp_dir, f"2025_09_11-{ref_version}-backup")
        
        # 尝试读取该股票的模拟结果summary
        summary_file = os.path.join(ref_dir, f"{stock_id}.json")
        
        if not os.path.exists(summary_file):
            return None
            
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('summary', {})
        except Exception as e:
            logger.warning(f"读取模拟结果失败 {stock_id}: {e}")
            return None

    def get_stock_data(self, stock_id: str, ref_version: str = None) -> Optional[Dict[str, Any]]:
        """
        获取指定股票的完整模拟结果数据（包括summary和investments）
        
        Args:
            stock_id: 股票ID
            ref_version: 参考版本号，如果为None则使用默认版本
            
        Returns:
            Dict[str, Any]: 完整的股票数据，如果不存在则返回None
        """
        # 获取参考版本号
        if ref_version is None:
            ref_version = "524"  # 默认参考版本
        
        # 构建参考结果目录路径
        ref_dir = os.path.join(self.tmp_dir, f"2025_09_11-{ref_version}-backup")
        
        # 尝试读取该股票的完整模拟结果数据
        data_file = os.path.join(ref_dir, f"{stock_id}.json")
        
        if not os.path.exists(data_file):
            return None
            
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取完整模拟结果失败 {stock_id}: {e}")
            return None

    def get_session_summary(self, session_id: str = None) -> Optional[Dict[str, Any]]:
        """
        获取指定会话的汇总信息
        
        Args:
            session_id: 会话ID，如果为None则使用当前会话
            
        Returns:
            Dict[str, Any]: 会话汇总信息，如果不存在则返回None
        """
        if session_id is None:
            session_id = self.current_session_id
        
        # 构建会话目录路径
        session_dir = os.path.join(self.tmp_dir, f"{datetime.now().strftime('%Y_%m_%d')}-{session_id}")
        summary_file = os.path.join(session_dir, "session_summary.json")
        
        if not os.path.exists(summary_file):
            return None
            
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取会话汇总失败 {session_id}: {e}")
            return None

    def list_sessions(self) -> list:
        """
        列出所有可用的会话
        
        Returns:
            list: 会话ID列表
        """
        sessions = []
        if not os.path.exists(self.tmp_dir):
            return sessions
        
        for item in os.listdir(self.tmp_dir):
            if os.path.isdir(os.path.join(self.tmp_dir, item)) and item != "meta.json":
                # 提取会话ID（格式：YYYY_MM_DD-session_id）
                parts = item.split('-')
                if len(parts) >= 2:
                    sessions.append(parts[1])
        
        return sorted(sessions)

    # ========================================================
    # Utils:
    # ========================================================

    def _save_json_to_file(self, data: Dict[str, Any], file_path: str) -> None:
        """通用的JSON保存方法，处理datetime序列化"""
        # 自定义JSON编码器，处理datetime对象
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    def get_current_session_id(self) -> str:
        """获取当前会话ID"""
        return self.current_session_id

    def get_tmp_dir(self) -> str:
        """获取tmp目录路径"""
        return self.tmp_dir
