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

    def get_latest_session_id(self):
        """获取最新的会话ID"""
        if not os.path.exists(self.tmp_dir):
            return None
        
        # 获取所有会话目录
        session_dirs = []
        for item in os.listdir(self.tmp_dir):
            item_path = os.path.join(self.tmp_dir, item)
            if os.path.isdir(item_path) and item.startswith("20"):  # 以日期开头的目录
                session_dirs.append(item)
        
        if not session_dirs:
            return None
        
        # 按目录名排序，获取最新的
        session_dirs.sort(reverse=True)
        latest_dir = session_dirs[0]
        
        # 从目录名中提取会话ID (格式: YYYY_MM_DD-session_id)
        if '-' in latest_dir:
            session_id = latest_dir.split('-')[1]
            return session_id
        
        return None

    def _find_session_dir(self, session_id: str):
        """根据会话ID查找对应的目录"""
        if not os.path.exists(self.tmp_dir):
            return None
        
        # 查找包含指定session_id的目录
        for item in os.listdir(self.tmp_dir):
            item_path = os.path.join(self.tmp_dir, item)
            if os.path.isdir(item_path) and item.endswith(f"-{session_id}"):
                return item_path
        
        return None


    # ========================================================
    # read simulation results:
    # ========================================================
    
    def get_simulation_session_summary(self, session_id: str = None) -> Dict[str, Any]:
        """
        获取模拟会话汇总
        
        Args:
            session_id: 会话ID，如果为None则使用最新的会话ID
            
        Returns:
            Dict[str, Any]: 会话汇总数据
        """
        if session_id is None:
            session_id = self.get_latest_session_id()
            if session_id is None:
                return {}
        
        # 查找对应的会话目录
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            logger.warning(f"未找到会话ID {session_id} 对应的目录")
            return {}
        
        # 读取会话汇总文件
        summary_file = os.path.join(session_dir, "session_summary.json")
        if not os.path.exists(summary_file):
            logger.warning(f"会话汇总文件不存在: {summary_file}")
            return {}
        
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            return summary_data
        except Exception as e:
            logger.error(f"❌ 读取会话汇总文件失败: {e}")
            return {}


    def get_simulation_stock_summary(self, stock_id: str, session_id: str = None) -> Dict[str, Any]:
        """
        获取模拟股票汇总
        
        Args:
            session_id: 会话ID，如果为None则使用最新的会话ID
            stock_id: 股票ID
            
        Returns:
            Dict[str, Any]: 股票汇总数据
        """
        if session_id is None:
            session_id = self.get_latest_session_id()
            if session_id is None:
                return {}
        
        # 查找对应的会话目录
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            logger.warning(f"未找到会话ID {session_id} 对应的目录")
            return {}
        
        # 读取股票汇总文件
        stock_file = os.path.join(session_dir, f"{stock_id}.json")
        if not os.path.exists(stock_file):
            logger.warning(f"股票 {stock_id} 的汇总文件不存在: {stock_file}")
            return {}
        
        try:
            with open(stock_file, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
            return stock_data
        except Exception as e:
            logger.error(f"❌ 读取股票 {stock_id} 汇总文件失败: {e}")
            return {}

    def get_simulation_stock_summary_by_list(self, session_id: str = None, stock_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        获取模拟股票汇总列表
        
        Args:
            session_id: 会话ID，如果为None则使用最新的会话ID
            stock_ids: 股票ID列表，如果为None或空列表则返回所有股票的汇总
            
        Returns:
            List[Dict[str, Any]]: 股票汇总数据列表
        """
        # 如果session_id为空，使用最新的会话ID
        if session_id is None:
            session_id = self.get_latest_session_id()
            if session_id is None:
                return []
        
        # 查找对应的会话目录
        session_dir = self._find_session_dir(session_id)
        if session_dir is None:
            logger.warning(f"未找到会话ID {session_id} 对应的目录")
            return []
        
        results = []
        
        # 如果stock_ids为空或None，获取所有股票的汇总
        if not stock_ids:
            if os.path.exists(session_dir):
                for item in os.listdir(session_dir):
                    if item.endswith('.json') and item != 'session_summary.json':
                        stock_id = item[:-5]  # 移除.json后缀
                        stock_file = os.path.join(session_dir, item)
                        try:
                            with open(stock_file, 'r', encoding='utf-8') as f:
                                stock_data = json.load(f)
                            results.append(stock_data)
                        except Exception as e:
                            logger.error(f"❌ 读取股票 {stock_id} 汇总文件失败: {e}")
        else:
            # 逐个读取指定股票的汇总文件
            for stock_id in stock_ids:
                stock_file = os.path.join(session_dir, f"{stock_id}.json")
                if os.path.exists(stock_file):
                    try:
                        with open(stock_file, 'r', encoding='utf-8') as f:
                            stock_data = json.load(f)
                        results.append(stock_data)
                    except Exception as e:
                        logger.error(f"❌ 读取股票 {stock_id} 汇总文件失败: {e}")
                else:
                    logger.warning(f"股票 {stock_id} 的汇总文件不存在: {stock_file}")
        
        return results

    def get_simulation_results(self, session_id: str = None) -> Dict[str, Any]:
        """
        获取模拟所有股票汇总
        
        Args:
            session_id: 会话ID，如果为None则使用最新的会话ID
            
        Returns:
            Dict[str, Any]: 包含session summary和stocks的完整模拟结果
        """
        # 获取会话汇总数据
        session_summary = self.get_simulation_session_summary(session_id)
        
        # 获取所有股票汇总数据（不指定stock_ids则返回所有）
        stock_summaries = self.get_simulation_stock_summary_by_list(session_id, None)
        
        return {
            "session": session_summary,
            "stocks": stock_summaries
        }

