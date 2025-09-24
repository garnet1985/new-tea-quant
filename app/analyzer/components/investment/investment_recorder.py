#!/usr/bin/env python3
"""
投资记录器 - 记录投资结算信息，支持基于策略和会话ID的存储管理
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger


class InvestmentRecorder:
    """投资记录器 - 记录投资结算信息，支持基于策略和会话ID的存储管理"""
    
    def __init__(self):
        """
        初始化投资记录器
        
        Args:
            strategy_name: 策略名称，用于确定存储路径
            session_id: 会话ID，如果为None则自动生成
        """
        self.strategy_folder_name = None
        self.tmp_dir = None
        self.meta_file = None
        self.current_session_id = None
        
    def set_strategy_folder_name(self, strategy_folder_name: str):
        """设置策略根目录"""
        self.strategy_folder_name = strategy_folder_name
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        strategy_dir = os.path.join(project_root, "app", "analyzer", "strategy", self.strategy_folder_name)
        self.tmp_dir = os.path.join(strategy_dir, "tmp")
        self.meta_file = os.path.join(self.tmp_dir, "meta.json")
        os.makedirs(self.tmp_dir, exist_ok=True)
        # 初始化meta.json文件
        self._init_meta_file()
        # 获取当前会话ID
        self.current_session_id = self._get_next_session_id()

    # ========================================================
    # Meta:
    # ========================================================

    def _init_meta_file(self):
        """初始化meta.json文件"""
        if not os.path.exists(self.meta_file):
            meta = {
                "next_session_id": 1,
                "last_updated": datetime.now().isoformat(),
                "strategy_name": self.strategy_folder_name
            }
            with open(self.meta_file, "w", encoding="utf-8") as file:
                json.dump(meta, file, ensure_ascii=False, indent=2)

    def _update_meta_file(self):
        """更新meta.json文件"""
        meta = {
            "next_session_id": self.current_session_id + 1,
            "last_updated": datetime.now().isoformat(),
            "strategy_name": self.strategy_folder_name
        }
        with open(self.meta_file, "w", encoding="utf-8") as file:
            json.dump(meta, file, ensure_ascii=False, indent=2)

        
    # ========================================================
    # save summary:
    # ========================================================

    def save_simulation_results(self, stock_summaries: List[Dict[str, Any]], session_summary: Dict[str, Any]) -> None:
        """保存模拟结果到文件"""
        # 获取当前session目录
        session_dir = self._create_session_dir()
        os.makedirs(session_dir, exist_ok=True)

        self.save_stock_summaries(stock_summaries, session_dir)
        self.save_session_summary(session_summary, session_dir)
        self._update_meta_file()
        
        logger.info(f"📝 会话汇总已保存: {session_dir}")


    def save_stock_summaries(self, stock_summaries: List[Dict[str, Any]], session_dir: str) -> None:
        """保存股票汇总信息到文件"""

        for stock_summary in stock_summaries:
            # 生成文件名
            stock_id = stock_summary['stock']['id']
            file_path = os.path.join(session_dir, f"{stock_id}.json")
            # 保存到文件
            self._save_json_to_file(stock_summary, file_path)


    def save_session_summary(self, session_summary: Dict[str, Any], session_dir: str) -> None:
        """生成会话汇总"""
       
        summary_file_path = os.path.join(session_dir, "session_summary.json")
        self._save_json_to_file(session_summary, summary_file_path)        
        return session_summary
    
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
    
    def _create_session_dir(self):
        """创建当前会话目录路径"""
        session_name = f"{datetime.now().strftime('%Y_%m_%d')}-{self.current_session_id}"
        return os.path.join(self.tmp_dir, session_name)

    def _get_next_session_id(self):
        """获取下一个会话ID"""
        with open(self.meta_file, "r", encoding="utf-8") as file:
            meta = json.load(file)
        return meta.get("next_session_id", 1)