"""
EngineConfigMeta — DatabaseManager 解析配置后传入 Engine 的只读元信息。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict

from core.infra.db.core.engines.shared.batch_write_settings import (
    BatchWriteSettings,
    parse_batch_write,
)

if TYPE_CHECKING:
    from core.infra.db.core.engines.duckdb.settings import DuckdbSettings
    from core.infra.db.core.engines.mysql.settings import MysqlSettings
    from core.infra.db.core.engines.pgsql.settings import PgsqlSettings


@dataclass(frozen=True)
class EngineConfigMeta:
    """
    DatabaseManager 挂载 Engine 前构造的配置快照；Engine 只读，不回写。

    ``backend`` 为类型化配置；``backend_config`` 为 merge 后的 dict 视图。
    """

    engine_key: str
    raw_config: Dict[str, Any] = field(default_factory=dict)
    backend_config: Dict[str, Any] = field(default_factory=dict)
    batch_write: BatchWriteSettings = field(default_factory=BatchWriteSettings)
    backend: Any = None
    options: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_raw_config(
        raw_config: Dict[str, Any], *, is_verbose: bool = False
    ) -> "EngineConfigMeta":
        """从 ``ConfigManager.load_database_config`` + ``parse_database_config`` 后的 dict 构造 meta。"""
        database_type = str(raw_config.get("database_type", "postgresql")).lower()
        backend_config = dict(raw_config.get(database_type) or {})
        batch_write = parse_batch_write(raw_config.get("batch_write"))

        if database_type == "mysql":
            from core.infra.db.core.engines.mysql.settings import MysqlSettings

            backend = MysqlSettings.from_dict(backend_config)
        elif database_type == "postgresql":
            from core.infra.db.core.engines.pgsql.settings import PgsqlSettings

            backend = PgsqlSettings.from_dict(backend_config)
        elif database_type == "duckdb":
            from core.infra.db.core.engines.duckdb.settings import DuckdbSettings

            backend = DuckdbSettings.from_dict(backend_config)
        else:
            raise ValueError(f"不支持的 database_type: {database_type!r}")

        options: Dict[str, Any] = {"is_verbose": is_verbose}
        if database_type == "duckdb":
            options["checkpoint_after_write"] = backend.checkpoint_after_write
            options["checkpoint_after_batch_save"] = backend.checkpoint_after_batch_save
            options["checkpoint_after_tag_run"] = backend.checkpoint_after_tag_run
            options["checkpoint_on_sigint"] = backend.checkpoint_on_sigint
            options["checkpoint_after_persist"] = backend.checkpoint_after_persist

        return EngineConfigMeta(
            engine_key=database_type,
            raw_config=raw_config,
            backend_config=backend_config,
            batch_write=batch_write,
            backend=backend,
            options=options,
        )

    def require_mysql(self) -> "MysqlSettings":
        from core.infra.db.core.engines.mysql.settings import MysqlSettings

        if self.engine_key != "mysql":
            raise TypeError(f"当前 backend 不是 mysql: {self.engine_key!r}")
        return self.backend  # type: ignore[return-value]

    def require_pgsql(self) -> "PgsqlSettings":
        if self.engine_key != "postgresql":
            raise TypeError(f"当前 backend 不是 postgresql: {self.engine_key!r}")
        return self.backend  # type: ignore[return-value]

    def require_duckdb(self) -> "DuckdbSettings":
        if self.engine_key != "duckdb":
            raise TypeError(f"当前 backend 不是 duckdb: {self.engine_key!r}")
        return self.backend  # type: ignore[return-value]
