"""
Entity Meta Management - Scenario 和 Tag 元信息管理

职责：
1. 确保 scenario 存在（如果不存在则创建）
2. 确保 tag definitions 存在（如果不存在则创建）
3. 提供统一的元信息管理接口
"""
from app.tag.core.components.entity_management.entity_meta_manager import EntityMetaManager

__all__ = ['EntityMetaManager']
