"""
MysqlSettings — merge 后 mysql 块的结构化配置。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class MysqlSettings:
    host: str
    port: int
    database: str
    user: str
    password: str
    charset: str = "utf8mb4"
    autocommit: bool = True
    pool_minconn: int = 1
    pool_maxconn: int = 10

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MysqlSettings:
        d = dict(data or {})
        pool_max = d.get("pool_maxconn", d.get("pool_size_max", d.get("pool_size", 10)))
        pool_min = d.get("pool_minconn", d.get("pool_size_min", 1))
        return cls(
            host=str(d["host"]),
            port=int(d.get("port", 3306)),
            database=str(d["database"]),
            user=str(d["user"]),
            password=str(d["password"]),
            charset=str(d.get("charset", "utf8mb4")),
            autocommit=bool(d.get("autocommit", True)),
            pool_minconn=max(1, int(pool_min)),
            pool_maxconn=max(1, int(pool_max)),
        )

    def as_dict(self) -> Dict[str, Any]:
        """Connector / 旧路径使用的扁平 dict。"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "charset": self.charset,
            "autocommit": self.autocommit,
            "pool_minconn": self.pool_minconn,
            "pool_maxconn": self.pool_maxconn,
        }
