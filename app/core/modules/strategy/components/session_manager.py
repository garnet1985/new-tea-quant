#!/usr/bin/env python3
"""
Session Manager - Session 管理器

职责：
- 生成 session_id
- 管理 session 元信息（meta.json）
"""

from pathlib import Path
from typing import Dict, Any
import json
import logging
from datetime import datetime

from app.core.infra.project_context import PathManager

logger = logging.getLogger(__name__)


class SessionManager:
    """Session 管理器"""
    
    def __init__(self, strategy_name: str):
        """
        初始化 Session 管理器
        
        Args:
            strategy_name: 策略名称
        """
        self.strategy_name = strategy_name
        self.results_path = PathManager.strategy_results(strategy_name)
        self.meta_file = self.results_path / "meta.json"
    
    def create_session(self) -> str:
        """
        创建新 session
        
        Returns:
            session_id: 新的 session ID（如 'session_001'）
        
        流程：
        1. 读取 meta.json 获取 next_session_id
        2. 生成新的 session_id
        3. 更新 meta.json
        """
        # 1. 读取 meta.json
        meta = self._load_meta()
        
        # 2. 生成 session_id
        next_id = meta.get('next_session_id', 1)
        session_id = f"session_{next_id:03d}"
        
        # 3. 更新 meta.json
        meta['next_session_id'] = next_id + 1
        meta['last_updated'] = datetime.now().isoformat()
        self._save_meta(meta)
        
        logger.info(f"📝 创建 Session: {session_id}")
        return session_id
    
    def _load_meta(self) -> Dict[str, Any]:
        """
        加载 meta.json
        
        Returns:
            meta: {
                'next_session_id': 1,
                'last_updated': '2025-12-19T10:30:00',
                'strategy_name': 'momentum'
            }
        """
        if not self.meta_file.exists():
            return {
                'next_session_id': 1,
                'strategy_name': self.strategy_name
            }
        
        with open(self.meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_meta(self, meta: Dict[str, Any]):
        """保存 meta.json"""
        self.results_path.mkdir(parents=True, exist_ok=True)
        
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
