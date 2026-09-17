"""决策者命令行 SQL 模式。

本文件:
- DecisionRepl: 录入中 / 账单中 / 已结束；Ctrl+C 存档离开
  边界: 不跑 ``cli.py s``；短命令在 infra.cli 注册
"""

from __future__ import annotations

import logging
import shlex
import sys
from typing import Any, Dict, List, Optional, TextIO, Tuple

from core.modules.strategy.core.engines.decision_maker.data_class import (
    AdvanceResult,
    ExitNotice,
)
from core.modules.strategy.core.engines.decision_maker.display import (
    format_date,
    format_money,
    format_pct,
    format_shares,
)
from core.modules.strategy.core.engines.decision_maker.engine import (
    PHASE_CONFIRMING,
    PHASE_PICKING,
    DecisionEngine,
)
from core.modules.strategy.core.engines.decision_maker.exceptions import DecisionError
from core.modules.strategy.core.engines.decision_maker.timeline import (
    DayOpportunity,
    format_status_tags,
)

logger = logging.getLogger(__name__)

_HELP = """命令:
  <编号>:<股数>   选择当日机会（同一编号再输入则覆盖）
  done            看账单
  next            提交当天并推进到下一事件日（须先 done）
  reset           清空草稿，留在当天
  holdings        持仓（status / holding 同义）
  info <编号|代码> [N] [字段,...]
                  截至今日最近 N 根开市日（默认 60，最大 252）
  help            本说明
  quit            存档并离开（Ctrl+C 相同）
"""


class DecisionRepl:
    """决策者命令行 SQL 模式。"""

    def __init__(
        self,
        engine: DecisionEngine,
        *,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
    ) -> None:
        self.engine = engine
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout

    def run(self) -> int:
        self._banner()
        if self.engine.is_completed:
            self._print_completed()
        else:
            self._print_day(announce=True)
        while True:
            try:
                line = self._read()
            except KeyboardInterrupt:
                self._writeln("")
                self._quit()
                return 0
            if line is None:
                self._quit()
                return 0
            text = str(line).strip()
            if not text:
                continue
            try:
                cont = self._dispatch(text)
            except DecisionError as exc:
                self._writeln(str(exc))
                continue
            except KeyboardInterrupt:
                self._writeln("")
                self._quit()
                return 0
            if not cont:
                return 0

    def _read(self) -> Optional[str]:
        prompt = self._prompt()
        try:
            self.stdout.write(prompt)
            self.stdout.flush()
            line = self.stdin.readline()
        except EOFError:
            return None
        if line == "":
            return None
        return line

    def _prompt(self) -> str:
        eng = self.engine
        date = format_date(eng.current_date)
        cash = format_money(eng.account.cash)
        n = eng.account.open_position_count()
        return f"{date} | 现金 {cash} | 持仓 {n} > "

    def _dispatch(self, text: str) -> bool:
        lower = text.lower()
        if lower in {"quit", "exit", "q"}:
            self._quit()
            return False
        if lower in {"help", "?"}:
            self._writeln(_HELP.strip())
            return True
        if lower in {"holdings", "holding", "status"}:
            self._print_holdings()
            return True
        if lower == "done":
            self._print_bill(self.engine.done())
            return True
        if lower == "reset":
            self.engine.reset()
            self._writeln("已清空选择")
            self._print_day(announce=False)
            return True
        if lower == "next":
            result = self.engine.next()
            self._print_advance(result)
            return True
        if lower.startswith("info"):
            tokens = _split_cmd(text)[1:]
            self._print_info(self.engine.info(tokens))
            return True
        pick = _parse_pick(text)
        if pick is not None:
            local_id, shares = pick
            opp, n, notional = self.engine.set_pick(local_id, shares)
            label = _stock_label(opp.name, opp.entity_id, opp.status_tags)
            self._writeln(
                f"✓ 已选择: [{opp.local_id}] {label}  {format_shares(n)} 股  "
                f"约 {format_money(notional)} 元"
            )
            return True
        self._writeln("无法识别。输入 help 查看命令。")
        return True

    def _banner(self) -> None:
        eng = self.engine
        self._writeln(
            f"决策者  session {eng.dm_id}  version {eng.version_id}  {eng.strategy_key}"
        )

    def _print_completed(self) -> None:
        self._writeln("本局已走完。可 holdings / info 查看，或 quit 离开。")
        try:
            from core.modules.strategy import Strategy
            from core.modules.strategy.contracts import SimulateKind

            Strategy.present_report(
                SimulateKind.PORTFOLIO,
                self.engine.store.session_dir(self.engine.dm_id),
                stream=self.stdout,
            )
        except Exception as exc:
            logger.debug("决策者终局展示跳过: %s", exc)
            self._writeln("终局报告已写在本局目录。")

    def _print_day(self, *, announce: bool) -> None:
        opps = self.engine.opportunities()
        if announce:
            self._writeln("发现了新的机会！" if opps else "今日无新机会。")
        for opp in opps:
            name = _stock_label(opp.name, opp.entity_id, opp.status_tags)
            ticker = opp.ticker_stats
            wr = format_pct(ticker.win_rate if ticker else None)
            roi = format_pct(ticker.avg_roi if ticker else None, signed=True)
            self._writeln(
                f"  [{opp.local_id}] {opp.entity_id} {name}  "
                f"买入价: {opp.entry_price_raw:.2f}  "
                f"历史胜率: {wr}  平均ROI: {roi}"
            )
        if self.engine.phase == PHASE_PICKING:
            self._writeln("输入 <编号>:<股数> 添加选择，或输入 done 确认")
        elif self.engine.phase == PHASE_CONFIRMING:
            self._writeln("请输入 next 继续推进，或 reset 重新下单")

    def _print_bill(self, bill: List[Tuple[DayOpportunity, int, float]]) -> None:
        if not bill:
            self._writeln("当前选择: （空，本日不买）")
        else:
            self._writeln("当前选择:")
            total = 0.0
            for opp, shares, notional in bill:
                total += float(notional)
                label = _stock_label(opp.name, opp.entity_id, opp.status_tags)
                self._writeln(
                    f"  [{opp.local_id}] {label}  {format_shares(shares)} 股  "
                    f"约 {format_money(notional)} 元"
                )
            self._writeln(
                f"  合计: {format_money(total)} 元  "
                f"(现金: {format_money(self.engine.account.cash)} 元)"
            )
        self._writeln("请输入 next 继续推进，或 reset 重新下单")

    def _print_advance(self, result: AdvanceResult) -> None:
        for notice in result.logs:
            self._print_exit(notice)
        if result.completed:
            self._print_completed()
            return
        self._print_day(announce=True)

    def _print_exit(self, notice: ExitNotice) -> None:
        label = _stock_label(notice.name, notice.entity_id, notice.status_tags)
        why = notice.goal_names or notice.reason or "纪律出场"
        sign = "+" if notice.profit >= 0 else ""
        self._writeln(
            f"  [{format_date(notice.date)}] 出场 {label}  "
            f"{format_shares(notice.shares)} 股  盈亏 {sign}{format_money(notice.profit)}  "
            f"({why})"
        )

    def _print_holdings(self) -> None:
        rows = self.engine.holdings()
        if not rows:
            self._writeln("当前无持仓")
            return
        for row in rows:
            label = _stock_label(row.name, row.entity_id, row.status_tags)
            if row.unrealized is None:
                pnl = "—"
            else:
                sign = "+" if row.unrealized >= 0 else ""
                pnl = f"{sign}{format_money(row.unrealized)}"
            close = f"{row.close:.2f}" if row.close is not None else "—"
            self._writeln(
                f"  {row.entity_id} {label}  {format_shares(row.shares)} 股  "
                f"买入 {format_date(row.buy_date)} @ {row.buy_price:.2f}  "
                f"持有 {_hold_span_text(row)}  收盘 {close}  浮动 {pnl}"
            )
            for goal in row.goals:
                self._writeln(f"    {goal}")

    def _print_info(self, payload: Dict[str, Any]) -> None:
        entity = payload.get("entity_id") or ""
        name = _stock_label(
            payload.get("name") or "",
            entity,
            payload.get("status_tags") or (),
        )
        stats = payload.get("stats") or {}
        ticker = payload.get("ticker_stats") or {}
        self._writeln(
            f"{entity} {name}  as-of {format_date(str(payload.get('as_of') or ''))}"
        )
        self._writeln(
            "  策略 "
            f"胜率 {format_pct(stats.get('win_rate'))}  "
            f"平均ROI {format_pct(stats.get('avg_roi'), signed=True)}  "
            f"n={stats.get('sample_size') or 0}"
            "  |  本标的 "
            f"胜率 {format_pct(ticker.get('win_rate'))}  "
            f"平均ROI {format_pct(ticker.get('avg_roi'), signed=True)}"
        )
        cols: List[str] = list(payload.get("columns") or [])
        rows = list(payload.get("rows") or [])
        if not cols or not rows:
            self._writeln("  （无 K 线）")
            return
        widths = [len(c) for c in cols]
        rendered: List[List[str]] = []
        for row in rows:
            cells: List[str] = []
            for i, col in enumerate(cols):
                text = _cell(row.get(col))
                cells.append(text)
                widths[i] = max(widths[i], len(text))
            rendered.append(cells)
        header = "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
        self._writeln(header)
        for cells in rendered:
            self._writeln(
                "  ".join(cells[i].ljust(widths[i]) for i in range(len(cols)))
            )

    def _quit(self) -> None:
        try:
            self.engine.save()
        except Exception as exc:
            logger.exception("决策者存档失败: %s", exc)
        self._writeln("已存档，离开决策者。")

    def _writeln(self, text: str = "") -> None:
        self.stdout.write(text + "\n")
        self.stdout.flush()


def _stock_label(name: str, entity_id: str, tags: Any = ()) -> str:
    base = str(name or "").strip() or str(entity_id or "").strip() or "—"
    status = format_status_tags(tags or ())
    return f"{base} {status}".strip() if status else base


def _hold_span_text(row: Any) -> str:
    unit = str(getattr(row, "hold_unit", "") or "").strip().lower()
    if unit == "trading_day":
        suffix = "个交易日"
    elif unit == "open_day":
        suffix = "个开市日"
    else:
        suffix = "个自然日"
    return f"{int(getattr(row, 'hold_days', 0) or 0)} {suffix}"


def _parse_pick(text: str) -> Optional[Tuple[int, int]]:
    if ":" not in text:
        return None
    left, right = text.split(":", 1)
    left = left.strip()
    right = right.strip().replace(",", "")
    if not left.isdigit() or not right.isdigit():
        return None
    return int(left), int(right)


def _split_cmd(text: str) -> List[str]:
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:.2f}"
        return f"{value:.4g}"
    return str(value)


__all__ = ["DecisionRepl"]
