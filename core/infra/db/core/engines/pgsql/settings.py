"""
PgsqlSettings — merge 后 postgresql 块的结构化配置。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class PgsqlSettings:
    host: str
    port: int
    database: str
    user: str
    password: str
    pgsql_schema: str = "public"
    pool_minconn: int = 1
    pool_maxconn: int = 10

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PgsqlSettings:
        d = dict(data or {})
        pool_size = int(d.get("pool_size", d.get("pool_maxconn", 10)))
        return cls(
            host=str(d["host"]),
            port=int(d.get("port", 5432)),
            database=str(d["database"]),
            user=str(d["user"]),
            password=str(d["password"]),
            pgsql_schema=str(
                d.get("pgsql_schema") or d.get("default_pgsql_schema") or "public"
            ),
            pool_minconn=int(d.get("pool_minconn", 1)),
            pool_maxconn=int(d.get("pool_maxconn", pool_size)),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "pgsql_schema": self.pgsql_schema,
            "default_pgsql_schema": self.pgsql_schema,
            "pool_minconn": self.pool_minconn,
            "pool_maxconn": self.pool_maxconn,
            "pool_size": self.pool_maxconn,
        }
