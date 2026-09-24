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
        shares: Optional[int] = None,
        cash: Optional[float] = None,
        note: Optional[str] = None,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        if cash is not None:
            engine.set_pick_cash(int(local_id), float(cash), note=note)
        else:
            engine.set_pick(int(local_id), int(shares or 0), note=note)
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
        keep_draft: bool = False,
    ) -> Dict[str, Any]:
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=str(session_id or "").strip(),
        )
        engine.reset(keep_draft=bool(keep_draft))
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
        payload = engine.info(tokens)
        msg = info_message(payload)
        msg["chart_layers"] = self._chart_layers_for_info(
            engine,
            strategy_key_or_name=strategy_key_or_name,
            entity_id=str(msg.get("entity_id") or ""),
            as_of=str(msg.get("as_of") or ""),
            candles=msg.get("candles") or [],
        )
        return msg

    @staticmethod
    def _chart_layers_for_info(
        engine: Any,
        *,
        strategy_key_or_name: str,
        entity_id: str,
        as_of: str,
        candles: List[Any],
    ) -> List[Dict[str, Any]]:
        """与报告单股图同形的 required 分层；失败不影响主 K。"""
        sid = str(entity_id or "").strip()
        if not sid:
            return []
        end = str(as_of or "").strip()
        start = ""
        if candles and isinstance(candles[0], dict):
            start = str(candles[0].get("date") or "").strip()
        if not end and candles and isinstance(candles[-1], dict):
            end = str(candles[-1].get("date") or "").strip()
        if not start or not end:
            return []
        try:
            from core.bff.APIs.strategy.routes.report.stock_detail import (
                WorkbenchStockDetail,
            )

            return WorkbenchStockDetail._load_chart_layers(
                sid,
                getattr(engine, "settings", None),
                {"start_date": start, "end_date": end},
                strategy_name=str(strategy_key_or_name or "").strip(),
            )
        except Exception:
            return []

    def get_report(
        self,
        strategy_key_or_name: str,
        session_id: str,
        *,
        version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """走完后的终局报告，形状与 portfolio ``capitalMetrics`` 相同。"""
        from pathlib import Path

        from core.bff.APIs.strategy.helpers.portfolio_event_timeline import (
            attach_portfolio_event_timeline,
        )
        from core.modules.strategy.core.engines.portfolio.report_manager.overall_report import (
            OverallReport,
        )
        from core.modules.strategy.core.services.artifacts.consts import (
            OVERALL_REPORT_FILE,
        )

        dm_id = str(session_id or "").strip()
        if not dm_id:
            raise ValueError("请指定 session")
        engine = self._open(
            strategy_key_or_name,
            version_id=version_id,
            session_id=dm_id,
        )
        if not engine.is_completed:
            raise ValueError("本次模拟回测尚未走完，没有报告")
        session_dir = Path(engine.store.session_dir(engine.dm_id))
        if not (session_dir / OVERALL_REPORT_FILE).is_file():
            engine.finalize()
        slot = OverallReport.load(session_dir).to_ui_dict()
        slot = attach_portfolio_event_timeline(slot, [session_dir])
        return {
            "dm_id": str(engine.dm_id or ""),
            "version_id": str(engine.version_id or ""),
            "report": slot if isinstance(slot, dict) else {},
        }


impl = StrategyDecisionImplementer()
