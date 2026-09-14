"""决策者 BFF implementer：打开 / 动作 / 现场 DTO。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.strategy import Strategy

from core.bff.APIs.strategy.helpers.decision_dto import (
    holdings_message,
    info_message,
    session_list_message,
    session_snapshot,
)


class StrategyDecisionImplementer:
    def lazy_load(self) -> "StrategyDecisionImplementer":
        return self

    def _resolve(self, strategy_key_or_name: str) -> str:
        return Strategy.resolve(strategy_key_or_name)

    def _open(
        self,
        strategy_key_or_name: str,
        *,
        version_id: Optional[str] = None,
        session_id: Optional[str] = None,
        new_session: bool = False,
    ):
        name = self._resolve(strategy_key_or_name)
        return Strategy.decision_open(
            name,
            version_id=version_id,
            session_id=session_id,
            new_session=new_session,
        )

    def list_sessions(
        self,
        strategy_key_or_name: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        name = self._resolve(strategy_key_or_name)
        return session_list_message(
            Strategy.decision_list(name, version_id=version_id)
        )

    def open_session(
        self,
        strategy_key_or_name: str,
        *,
        version_id: Optional[str] = None,
        session_id: Optional[str] = None,
        new_session: bool = False,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=session_id,
            new_session=new_session,
        )
        return session_snapshot(engine)

    def get_session(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        dm_id = str(session_id or "").strip()
        if not dm_id:
            raise ValueError("请指定 session")
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=dm_id,
        )
        return session_snapshot(engine)

    def delete_session(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        name = self._resolve(strategy_key_or_name)
        dm_id = str(session_id or "").strip()
        if not dm_id:
            raise ValueError("请指定 session")
        return Strategy.decision_delete(name, dm_id, version_id=version_id)

    def set_pick(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        local_id: int,
        shares: int,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        engine.set_pick(int(local_id), int(shares))
        return session_snapshot(engine)

    def done(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        engine.done()
        return session_snapshot(engine)

    def reset(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        engine.reset()
        return session_snapshot(engine)

    def next(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        result = engine.next()
        return session_snapshot(engine, exits=getattr(result, "logs", None) or ())

    def holdings(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        return holdings_message(engine, engine.holdings())

    def info(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        target: str,
        n: Optional[int] = None,
        columns: Optional[List[str]] = None,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        tokens: List[str] = [str(target or "").strip()]
        if not tokens[0]:
            raise ValueError("用法: info <编号|代码> [N] [字段,...]")
        if n is not None:
            tokens.append(str(int(n)))
        if columns:
            keep = [str(item).strip() for item in columns if str(item).strip()]
            if keep:
                tokens.append(",".join(keep))
        return info_message(engine.info(tokens))


impl = StrategyDecisionImplementer()
