"""
DuckdbSettings — merge 后 duckdb 块（含三域）的结构化配置。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from core.infra.db.storage_registry import STORAGE_DOMAINS


@dataclass(frozen=True)
class DuckdbDomainSettings:
    db_path: str
    read_only: bool = False
    threads: Optional[int] = None
    memory_limit: Optional[str] = None

    def as_dict(self, shared: Mapping[str, Any]) -> Dict[str, Any]:
        """域连接用：共享项 + 域覆盖。"""
        out: Dict[str, Any] = {
            k: v for k, v in shared.items() if k != "domains"
        }
        out["db_path"] = self.db_path
        out["read_only"] = self.read_only
        if self.threads is not None:
            out["threads"] = self.threads
        if self.memory_limit is not None:
            out["memory_limit"] = self.memory_limit
        return out


@dataclass(frozen=True)
class DuckdbSettings:
    domains: Dict[str, DuckdbDomainSettings]
    threads: Optional[int] = None
    memory_limit: Optional[str] = None
    wal_autocheckpoint: str | bool = "4MB"
    checkpoint_after_batch_save: bool = True
    checkpoint_after_tag_run: bool = True
    checkpoint_on_sigint: bool = True
    checkpoint_after_persist: bool = False
    recover_wal_on_replay_failure: bool = False

    @property
    def checkpoint_after_write(self) -> bool:
        """WritePipeline 批末 CHECKPOINT（对齐旧 options 名）。"""
        return self.checkpoint_after_batch_save

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DuckdbSettings:
        d = dict(data or {})
        raw_domains = d.get("domains")
        if not isinstance(raw_domains, dict) or not raw_domains:
            raise ValueError("DuckDB 配置缺少非空 domains")

        domains: Dict[str, DuckdbDomainSettings] = {}
        for name in sorted(STORAGE_DOMAINS):
            block = raw_domains.get(name)
            if not isinstance(block, dict) or not block.get("db_path"):
                raise ValueError(f"DuckDB domains 缺少域或 db_path: {name!r}")
            domains[name] = DuckdbDomainSettings(
                db_path=str(block["db_path"]),
                read_only=bool(block.get("read_only", False)),
                threads=block.get("threads"),
                memory_limit=block.get("memory_limit"),
            )

        wal_ac = d.get("wal_autocheckpoint", "4MB")
        return cls(
            domains=domains,
            threads=d.get("threads"),
            memory_limit=d.get("memory_limit"),
            wal_autocheckpoint=wal_ac if wal_ac is not False else False,
            checkpoint_after_batch_save=bool(
                d.get("checkpoint_after_batch_save", d.get("checkpoint_after_write", True))
            ),
            checkpoint_after_tag_run=bool(d.get("checkpoint_after_tag_run", True)),
            checkpoint_on_sigint=bool(d.get("checkpoint_on_sigint", True)),
            checkpoint_after_persist=bool(d.get("checkpoint_after_persist", False)),
            recover_wal_on_replay_failure=bool(
                d.get("recover_wal_on_replay_failure", False)
            ),
        )

    def shared_connector_dict(self) -> Dict[str, Any]:
        return {
            "threads": self.threads,
            "memory_limit": self.memory_limit,
            "wal_autocheckpoint": self.wal_autocheckpoint,
            "recover_wal_on_replay_failure": self.recover_wal_on_replay_failure,
            "checkpoint_after_batch_save": self.checkpoint_after_batch_save,
            "checkpoint_after_tag_run": self.checkpoint_after_tag_run,
            "checkpoint_on_sigint": self.checkpoint_on_sigint,
            "checkpoint_after_persist": self.checkpoint_after_persist,
        }

    def as_dict(self) -> Dict[str, Any]:
        """与 merge 后 duckdb 块兼容的 dict（供 wal_policy 等）。"""
        return {
            **self.shared_connector_dict(),
            "domains": {
                name: {
                    "db_path": dom.db_path,
                    "read_only": dom.read_only,
                    **(
                        {"threads": dom.threads}
                        if dom.threads is not None
                        else {}
                    ),
                    **(
                        {"memory_limit": dom.memory_limit}
                        if dom.memory_limit is not None
                        else {}
                    ),
                }
                for name, dom in self.domains.items()
            },
        }
