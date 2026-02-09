"""
PersistenceService - 负责将标准化数据写入绑定表。

当前实现与 BaseHandler._system_save 保持语义一致，仅做轻量封装，
方便后续在不影响 Handler 的情况下演进写库策略。
"""
from typing import Any, Dict, List, Optional

from loguru import logger

from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_manager.data_manager import DataManager


class PersistenceService:
    """根据 context 中的 config / data_manager / schema，将 normalized_data 写入绑定表。"""

    @staticmethod
    def save(context: Dict[str, Any], normalized_data: Dict[str, Any]) -> None:
        """
        将标准化数据写入绑定表（使用表 schema 的 primaryKey 做 upsert）。

        Args:
            context: 执行上下文，需包含 config / data_manager / schema
            normalized_data: 标准化后的数据，格式为 {"data": [...]}。
        """
        config: Optional[DataSourceConfig] = context.get("config")
        data_manager: Optional[DataManager] = context.get("data_manager")
        schema = context.get("schema")

        if not config or not data_manager or not schema:
            return

        table_name = config.get_table_name()
        if not table_name:
            return

        model = data_manager.get_table(table_name)
        if not model or not hasattr(model, "upsert_many"):
            logger.warning(f"表 {table_name} 未注册或无可用的 upsert_many，跳过系统写入")
            return

        records = (normalized_data or {}).get("data")
        if not records or not isinstance(records, list):
            logger.debug(f"系统写入 {table_name}: normalized_data 中没有数据或格式不正确，跳过写入")
            return

        original_count = len(records)
        pk = schema.get("primaryKey")
        if isinstance(pk, str):
            unique_keys: Optional[List[str]] = [pk]
        elif isinstance(pk, list):
            unique_keys = list(pk)
        else:
            unique_keys = None

        # 去重：如果配置了 unique_keys，在同一个批次中去重（保留最后一个）
        if unique_keys and len(unique_keys) > 0:
            seen = {}
            deduplicated_records = []
            for record in records:
                # 构建唯一键
                key_tuple = tuple(record.get(key) for key in unique_keys)
                if None not in key_tuple:  # 只处理所有 unique_keys 都有值的记录
                    seen[key_tuple] = record
            deduplicated_records = list(seen.values())
            records = deduplicated_records

        if not unique_keys or len(unique_keys) == 0:
            logger.warning(
                f"表 {table_name} 的 schema 未配置 primaryKey，无法确定 upsert 唯一键，跳过系统写入"
            )
            return

        try:
            affected = model.upsert_many(records, unique_keys)
            logger.info(
                f"系统写入 {table_name}: upsert {affected} 条记录"
                f"（原始 {original_count} 条，去重后 {len(records)} 条，unique_keys={unique_keys}）"
            )
        except Exception as e:
            logger.error(f"系统写入 {table_name} 失败: {e}")
            raise

