"""Investment — Opportunity 的模拟生命周期（enumerator / price 共用）。

消费者: scanner, enumerator, price_factor
其它: contracts

本文件:
- Investment: 生命周期反应 API（try_enter / check_targets / try_exit / settle）
  边界: 不自驱 tick；由 InvestmentTracker 按分桶调用；小类型见 ``investment/``
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    OpportunityContributor,
    OpportunityMeta,
    StockInfo,
)
from core.modules.strategy.core.engines.shared.data_class.investment import (
    DEFAULT_TARGET_CHECK_ORDER,
    EnterState,
    ExitReason,
    ExitState,
    ExpirationMode,
    ExtremeState,
    HoldingState,
    InvestmentState,
    InvestmentResult,
    Lifecycle,
    OutcomeState,
    PendingExit,
    PendingExitKind,
    TargetCheckStep,
    TradeSide,
)
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import SafeBarValue

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
        StrategySettings,
    )

@dataclass
class Investment(Opportunity):
    """Extends ``Opportunity`` with simulation state.

    完整生命周期（由 InvestmentTracker 分桶驱动）:
    机会 → ``create_from_opportunity``（``PENDING_TO_ENTER``）
      → ``try_enter``（条件未齐时挂起，如次日 open）
      → ``check_targets``（``OPEN``）
      → ``try_exit``（``PENDING_TO_EXIT``）
      → ``COMPLETE`` / ``settle``

    配置直接挂 ``settings``；另附 run 级 ``market_rules`` / ``open_dates`` /
    ``status_tags_provider``（非 settings 切片投影）。
    """

    runtime_state: InvestmentState = field(default_factory=InvestmentState)
    settings: Optional["StrategySettings"] = None
    market_rules: Any = None
    open_dates: Tuple[str, ...] = field(default_factory=tuple)
    status_tags_provider: Any = None

    _TARGET_CHECK_HANDLERS: ClassVar[Dict[TargetCheckStep, str]] = {
        TargetCheckStep.CHECK_STOP_LOSS: "_check_stop_loss",
        TargetCheckStep.CHECK_TAKE_PROFIT: "_check_take_profit",
        TargetCheckStep.CHECK_EXPIRATION: "_check_expiration",
    }

    @property
    def lifecycle(self) -> Lifecycle:
        return self.runtime_state.state

    @lifecycle.setter
    def lifecycle(self, value: Lifecycle) -> None:
        self.runtime_state.state = value

    @property
    def entry(self) -> EnterState:
        return self.runtime_state.entry

    @entry.setter
    def entry(self, value: EnterState) -> None:
        self.runtime_state.entry = value

    @property
    def exit_info(self) -> ExitState:
        return self.runtime_state.exit_info

    @exit_info.setter
    def exit_info(self, value: ExitState) -> None:
        self.runtime_state.exit_info = value

    @property
    def pending_exit(self) -> Optional[PendingExit]:
        return self.runtime_state.pending_exit

    @pending_exit.setter
    def pending_exit(self, value: Optional[PendingExit]) -> None:
        self.runtime_state.pending_exit = value

    @property
    def holding(self) -> HoldingState:
        return self.runtime_state.holding

    @holding.setter
    def holding(self, value: HoldingState) -> None:
        self.runtime_state.holding = value

    @property
    def extreme(self) -> ExtremeState:
        return self.runtime_state.extreme

    @extreme.setter
    def extreme(self, value: ExtremeState) -> None:
        self.runtime_state.extreme = value

    @property
    def outcome(self) -> OutcomeState:
        return self.runtime_state.outcome

    @outcome.setter
    def outcome(self, value: OutcomeState) -> None:
        self.runtime_state.outcome = value

    @property
    def completed_goals(self) -> List[Dict[str, Any]]:
        return self.runtime_state.completed_goals

    @classmethod
    def create_from_opportunity(
        cls,
        opportunity: Opportunity,
        *,
        settings: "StrategySettings",
        open_dates: Sequence[str],
        status_tags_provider: Any = None,
    ) -> "Investment":
        """从机会创建 Investment，初始 ``PENDING_TO_ENTER``（尚未成交）。"""
        from core.infra.project_context import ProjectContext
        from core.modules.market_profile.core.markets import create_market_rules

        profile = str(
            opportunity.market_profile or ProjectContext.config.get_default_market_profile_key()
        ).strip()
        opportunity.market_profile = profile
        opportunity.stamp_status_at_trigger(status_tags_provider=status_tags_provider)
        settings.apply_defaults()
        market_rules = create_market_rules(profile)
        holding = HoldingState()
        expiration = settings.goal.expiration
        if expiration is not None:
            holding.mode = ExpirationMode(expiration.mode)
            holding.window_days = int(expiration.window_days or 0)
        return cls(
            stock=opportunity.stock,
            record_of_today=dict(opportunity.record_of_today),
            trigger_date=str(opportunity.trigger_date or ""),
            trigger_price=float(opportunity.trigger_price or 0.0),
            trigger_price_raw=float(opportunity.trigger_price_raw or 0.0),
            market_profile=profile,
            meta=cls._copy_dataclass(opportunity.meta, OpportunityMeta),
            contributor=cls._copy_dataclass(opportunity.contributor, OpportunityContributor),
            extra_fields=dict(opportunity.extra_fields),
            metadata=dict(opportunity.metadata),
            settings=settings,
            market_rules=market_rules,
            open_dates=tuple(open_dates),
            status_tags_provider=status_tags_provider,
            runtime_state=InvestmentState(
                state=Lifecycle.PENDING_TO_ENTER,
                holding=holding,
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """JSON/CSV-safe export（省略 settings / market_rules 等非序列化依赖）。"""
        payload = Opportunity.to_dict(self)
        rs = self.runtime_state
        state = {
            "state": self.lifecycle.value,
            "entry": asdict(rs.entry),
            "exit_info": asdict(rs.exit_info),
            "holding": asdict(rs.holding),
            "extreme": asdict(rs.extreme),
            "outcome": asdict(rs.outcome),
            "completed_goals": list(self.completed_goals),
            "customized_state": dict(rs.customized_state or {}),
            "triggered_force_exit_tags": list(rs.triggered_force_exit_tags or []),
            "last_bar": rs.last_bar,
            "triggered_stop_loss_idx": rs.triggered_stop_loss_idx,
            "triggered_take_profit_idx": rs.triggered_take_profit_idx,
            "remaining_ratio": rs.remaining_ratio,
            "protect_loss_active": rs.protect_loss_active,
            "dynamic_loss_active": rs.dynamic_loss_active,
            "dynamic_loss_peak": rs.dynamic_loss_peak,
        }
        if rs.pending_exit is not None:
            state["pending_exit"] = asdict(rs.pending_exit)
        payload.update(
            {
                "lifecycle": self.lifecycle.value,
                "runtime_state": state,
                "entry": asdict(self.entry),
                "exit_info": asdict(self.exit_info),
                "holding": asdict(self.holding),
                "extreme": asdict(self.extreme),
                "outcome": asdict(self.outcome),
                "completed_goals": list(self.completed_goals),
                "target_check_order": [
                    step.value for step in self._resolve_target_check_order()
                ],
            }
        )
        if self.pending_exit is not None:
            payload["pending_exit"] = asdict(self.pending_exit)
        return payload

    def _resolve_target_check_order(self) -> List[TargetCheckStep]:
        if self.settings is not None:
            return list(self.settings.simulation.parsed_target_check_order())
        return list(DEFAULT_TARGET_CHECK_ORDER)

    def try_enter(self, as_of: str, bar: Dict[str, Any]) -> None:
        """``PENDING_TO_ENTER``：先判 abort，再尝试进场。

        - abort（超时 / 漂移 / status / 退市）→ ``COMPLETE``（无成交）
        - 今日能成交 → ``OPEN``
        - 否则继续挂（涨停挡买、未触及限价等）
        """
        if self.lifecycle != Lifecycle.PENDING_TO_ENTER:
            return
        as_of = str(as_of or "").strip()
        abort_reason = self.should_abort_enter(as_of, bar)
        if abort_reason:
            self._abort_enter(as_of, abort_reason)
            self._remember_bar(bar)
            return
        if self._is_able_to_enter(as_of, bar):
            self._apply_enter(as_of, bar)
            self.lifecycle = Lifecycle.OPEN
            self._update_extremes(as_of, bar)
            self._remember_bar(bar)
            return
        # 末日仍未成交：放弃
        if self._pending_wait_exhausted(as_of):
            self._abort_enter(as_of, "pending_enter:max_wait_open_days")
        self._remember_bar(bar)

    def check_targets(self, as_of: str, bar: Dict[str, Any]) -> None:
        """``OPEN``：更新极值/持有，评估 force_exit 与 goals；可能武装 ``PENDING_TO_EXIT`` 或完结。"""
        if self.lifecycle != Lifecycle.OPEN:
            return
        as_of = str(as_of or "").strip()
        self._update_extremes(as_of, bar)
        self._update_holding(as_of)
        self._process_open_exits(as_of, bar, check_force=True)
        self._remember_bar(bar)

    def try_exit(self, as_of: str, bar: Dict[str, Any]) -> None:
        """``PENDING_TO_EXIT``：尝试出场成交。

        全平 → ``COMPLETE``；部分平仓 → ``OPEN`` 并同 tick 再评估 goals（不含 force）。
        """
        if self.lifecycle != Lifecycle.PENDING_TO_EXIT:
            return
        as_of = str(as_of or "").strip()
        skip_tradability = self._exit_skips_tradability()
        if self._is_able_to_exit(
            as_of, bar, check_tradability=not skip_tradability
        ):
            self._apply_exit(
                as_of, bar, check_tradability=not skip_tradability
            )
            if self.runtime_state.remaining_ratio <= 1e-12:
                self.lifecycle = Lifecycle.COMPLETE
                self._remember_bar(bar)
                return
            self.lifecycle = Lifecycle.OPEN
            self._process_open_exits(as_of, bar, check_force=False)
            self._remember_bar(bar)
            return
        self._remember_bar(bar)

    def _process_open_exits(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        check_force: bool,
    ) -> bool:
        """处理 force_exit / goals；部分平仓后同 tick 再评估。返回是否继续跟踪。"""
        need_exit = self._check_force_exit(as_of, bar) if check_force else False
        for _ in range(8):
            if not need_exit:
                need_exit = self._evaluate_goals(as_of, bar)
            if not need_exit:
                break
            if self._should_defer_exit(as_of, bar):
                self._mark_pending_exit_kind(
                    PendingExitKind.NEXT_OPEN_DEFER, armed_as_of=as_of
                )
                self.lifecycle = Lifecycle.PENDING_TO_EXIT
                return True
            skip_tradability = self._exit_skips_tradability()
            if self._is_able_to_exit(
                as_of, bar, check_tradability=not skip_tradability
            ):
                self._apply_exit(
                    as_of, bar, check_tradability=not skip_tradability
                )
                if self.runtime_state.remaining_ratio <= 1e-12:
                    self.lifecycle = Lifecycle.COMPLETE
                    return False
                self.lifecycle = Lifecycle.OPEN
                need_exit = False
                continue
            self._mark_pending_exit_kind(PendingExitKind.FILL_RETRY, armed_as_of=as_of)
            self.lifecycle = Lifecycle.PENDING_TO_EXIT
            return True
        return True

    def _mark_pending_exit_kind(
        self,
        kind: PendingExitKind,
        *,
        armed_as_of: str = "",
    ) -> None:
        pending = self.pending_exit
        if pending is None:
            return
        pending.kind = kind.value
        if kind == PendingExitKind.NEXT_OPEN_DEFER:
            pending.armed_as_of = str(armed_as_of or "").strip()
        elif not pending.armed_as_of and armed_as_of:
            pending.armed_as_of = str(armed_as_of).strip()

    def _exit_skips_tradability(self) -> bool:
        """退市定价用 ``fill_bar`` 时不做贴板拦截（强平须成交）。"""
        pending = self.pending_exit
        return pending is not None and isinstance(pending.fill_bar, dict) and bool(
            pending.fill_bar
        )

    def _remember_bar(self, bar: Dict[str, Any]) -> None:
        self.runtime_state.last_bar = bar

    def _pending_exit_ratio(self) -> float:
        if self.pending_exit is None:
            return 1.0
        return float(self.pending_exit.exit_ratio or 1.0)

    def _check_force_exit(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """``RiskControl.should_force_exit``；命中则写 ``pending_exit``（先于 goals）。"""
        stock_meta: Dict[str, Any] = {}
        stock = self.stock
        if isinstance(stock, StockInfo):
            stock_meta = stock.to_dict()
        elif isinstance(stock, dict):
            stock_meta = dict(stock)
        decision = self.settings.simulation.risk_control.should_force_exit(
            entity_id=self._entity_id(),
            trade_date=str(as_of or "").strip(),
            status_tags=self._status_tags(bar),
            already_triggered=self.runtime_state.triggered_force_exit_tags,
            stock_meta=stock_meta,
        )
        if decision is None:
            return False
        reason = str(decision.reason or "").strip() or "stock_status_risk"
        tag = reason.split(":", 1)[-1] if ":" in reason else reason
        if tag and tag not in self.runtime_state.triggered_force_exit_tags:
            self.runtime_state.triggered_force_exit_tags.append(tag)
        if decision.close_invest:
            exit_ratio = 1.0
        else:
            exit_ratio = float(decision.exit_ratio)
        fill_bar = self._delisted_fill_bar(tag, bar)
        self.pending_exit = PendingExit(
            reason=reason,
            exit_ratio=exit_ratio,
            goal_name=reason,
            fill_bar=fill_bar,
        )
        return True

    def _delisted_fill_bar(
        self,
        tag: str,
        bar: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """退市强平：按 ``delisted_exit_price`` 选择成交 bar。"""
        if tag != "delisted":
            return None
        mode = str(
            self.settings.simulation.delisted_exit_price or "last_tradable_close"
        ).strip().lower()
        if mode == "same_tick_close":
            return None
        prev = self.runtime_state.last_bar
        if isinstance(prev, dict) and prev:
            return prev
        return None

    def _evaluate_goals(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """Settlement 门禁（写死）→ protect/dynamic → ``target_check_order`` 短路。"""
        if not self._check_settlement(as_of):
            return False
        if self._check_protect_loss(as_of, bar):
            return True
        if self._check_dynamic_loss(as_of, bar):
            return True
        for step in self._resolve_target_check_order():
            handler_name = self._TARGET_CHECK_HANDLERS[step]
            if getattr(self, handler_name)(as_of, bar):
                return True
        return False

    def _check_settlement(self, as_of: str) -> bool:
        """Gate: False blocks remaining steps for this bar."""
        if self.lifecycle != Lifecycle.OPEN:
            return True
        entry_date = str(self.entry.date or "").strip()
        if not entry_date:
            return True
        held = self._settlement_days_held(entry_date, as_of, self.open_dates)
        return self.market_rules.is_allowed_to_sell(held)

    def _monitor_px(self, bar: Dict[str, Any]) -> float:
        model = str(self.settings.simulation.monitor_price or "close").strip().lower() or "close"
        return SafeBarValue.price_for_model(bar, model, use_raw=False)

    def _arm_goal_exit(
        self,
        *,
        reason: str,
        exit_ratio: float,
        goal_name: str,
    ) -> bool:
        self.pending_exit = PendingExit(
            reason=reason,
            exit_ratio=float(exit_ratio),
            goal_name=goal_name,
        )
        return True

    def _check_protect_loss(self, as_of: str, bar: Dict[str, Any]) -> bool:
        _ = as_of
        if (
            self.lifecycle != Lifecycle.OPEN
            or not self.runtime_state.protect_loss_active
        ):
            return False
        cfg = self.settings.goal.protect_loss
        if cfg is None:
            return False
        basis = float(self.entry.price or self.trigger_price or 0.0)
        monitor = self._monitor_px(bar)
        if basis <= 0 or monitor <= 0:
            return False
        price_return = (monitor - basis) / basis
        if price_return > float(cfg.ratio):
            return False
        exit_ratio = 1.0 if cfg.close_invest else float(cfg.exit_ratio)
        return self._arm_goal_exit(
            reason=ExitReason.PROTECT_LOSS.value,
            exit_ratio=exit_ratio,
            goal_name=cfg.name,
        )

    def _check_dynamic_loss(self, as_of: str, bar: Dict[str, Any]) -> bool:
        _ = as_of
        if (
            self.lifecycle != Lifecycle.OPEN
            or not self.runtime_state.dynamic_loss_active
        ):
            return False
        cfg = self.settings.goal.dynamic_loss
        if cfg is None:
            return False
        monitor = self._monitor_px(bar)
        if monitor <= 0:
            return False
        basis = float(self.entry.price or self.trigger_price or 0.0)
        peak = self.runtime_state.dynamic_loss_peak
        if peak is None or peak <= 0:
            peak = basis if basis > 0 else monitor
        extreme_hi = self.extreme.highest
        if extreme_hi is not None and float(extreme_hi) > 0:
            peak = max(float(peak), float(extreme_hi))
        peak = max(float(peak), monitor)
        self.runtime_state.dynamic_loss_peak = peak
        drawdown = (monitor - peak) / peak if peak > 0 else 0.0
        if drawdown > float(cfg.ratio):
            return False
        exit_ratio = 1.0 if cfg.close_invest else float(cfg.exit_ratio)
        return self._arm_goal_exit(
            reason=ExitReason.DYNAMIC_LOSS.value,
            exit_ratio=exit_ratio,
            goal_name=cfg.name,
        )

    def _check_stop_loss(self, as_of: str, bar: Dict[str, Any]) -> bool:
        _ = as_of
        if self.lifecycle != Lifecycle.OPEN:
            return False
        stages = self.settings.goal.stop_loss_stages
        if not stages:
            return False
        basis = float(self.entry.price or self.trigger_price or 0.0)
        if basis <= 0:
            return False
        low = float(bar["low"])
        for idx, stage in enumerate(stages):
            if idx <= self.runtime_state.triggered_stop_loss_idx:
                continue
            stop_price = self.settings.goal.exit_price(stage, basis)
            if low > stop_price:
                continue
            self.runtime_state.triggered_stop_loss_idx = idx
            exit_ratio = 1.0 if stage.close_invest else float(stage.exit_ratio)
            return self._arm_goal_exit(
                reason=ExitReason.STOP_LOSS.value,
                exit_ratio=exit_ratio,
                goal_name=stage.name,
            )
        return False

    def _check_take_profit(self, as_of: str, bar: Dict[str, Any]) -> bool:
        _ = as_of
        if self.lifecycle != Lifecycle.OPEN:
            return False
        stages = self.settings.goal.take_profit_stages
        if not stages:
            return False
        basis = float(self.entry.price or self.trigger_price or 0.0)
        if basis <= 0:
            return False
        high = float(bar["high"])
        for idx, stage in enumerate(stages):
            if idx <= self.runtime_state.triggered_take_profit_idx:
                continue
            target_price = self.settings.goal.exit_price(stage, basis)
            if high < target_price:
                continue
            self.runtime_state.triggered_take_profit_idx = idx
            self._apply_take_profit_actions(stage, bar)
            exit_ratio = 1.0 if stage.close_invest else float(stage.exit_ratio)
            return self._arm_goal_exit(
                reason=ExitReason.TAKE_PROFIT.value,
                exit_ratio=exit_ratio,
                goal_name=stage.name,
            )
        return False

    def _apply_take_profit_actions(self, stage: Any, bar: Dict[str, Any]) -> None:
        actions = tuple(getattr(stage, "actions", ()) or ())
        for action in actions:
            if action == "set_protect_loss":
                self.runtime_state.protect_loss_active = True
            elif action == "set_dynamic_loss":
                self.runtime_state.dynamic_loss_active = True
                monitor = self._monitor_px(bar)
                high = float(bar.get("high") or 0.0) or monitor
                peak = max(monitor, high)
                prev = self.runtime_state.dynamic_loss_peak
                if prev is not None and prev > 0:
                    peak = max(peak, float(prev))
                self.runtime_state.dynamic_loss_peak = peak

    def _check_expiration(self, as_of: str, bar: Dict[str, Any]) -> bool:
        _ = bar
        if self.lifecycle != Lifecycle.OPEN:
            return False
        if int(self.holding.window_days or 0) <= 0 or self.holding.mode is None:
            return False
        entry_date = str(self.entry.date or "").strip()
        if not entry_date:
            return False
        held = self._holding_days(entry_date, as_of, self.holding.mode, self.open_dates)
        self.holding.days = held
        if held >= int(self.holding.window_days or 0):
            return self._arm_goal_exit(
                reason=ExitReason.EXPIRED.value,
                exit_ratio=1.0,
                goal_name="expiration",
            )
        return False

    def _should_defer_exit(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """True when ``exit_price`` requires a later tick to fill (MVP: ``next_open`` only)."""
        _ = (as_of, bar)
        pending = self.pending_exit
        # 已是贴板重试：不再按 next_open 延期逻辑处理
        if pending is not None and str(pending.kind or "") == PendingExitKind.FILL_RETRY.value:
            return False
        model = str(self.settings.simulation.exit_price or "close").strip().lower()
        return model == "next_open"

    def _pending_exit_fill_model(self) -> str:
        """PENDING_TO_EXIT 成交价模型：next_open_defer → open；否则用配置的 exit_price。"""
        pending = self.pending_exit
        if pending is not None and str(pending.kind or "") == PendingExitKind.NEXT_OPEN_DEFER.value:
            return "open"
        return str(self.settings.simulation.exit_price or "close").strip().lower() or "close"

    def _is_able_to_enter(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """Whether this tick can fill entry per ``enter_price`` (no mutation).

        ``False`` = 今天不成交、继续挂；放弃进场见 ``should_abort_enter``。
        """
        return self._resolve_entry_price(as_of, bar) is not None

    def should_abort_enter(self, as_of: str, bar: Dict[str, Any]) -> Optional[str]:
        """挂单硬取消：退市 / abort_enter_when / 等待超限 / 漂移超限。

        返回 reason 字符串；``None`` = 不 abort（仍可尝试成交或继续挂）。
        """
        if self.lifecycle != Lifecycle.PENDING_TO_ENTER:
            return None
        if self.settings is None:
            return None
        as_of = str(as_of or "").strip()
        policy = self.settings.simulation.risk_control.pending_enter

        stock_meta = self._stock_meta_dict()
        if self._is_delisted_on(stock_meta, as_of):
            return "pending_enter:delisted"

        status_hit = policy.abort_enter_when.match_reason(self._status_tags(bar))
        if status_hit:
            return f"pending_enter:{status_hit}"

        waited = self._pending_wait_open_days(as_of)
        attempts = self._pending_attempts_allowed(policy.max_wait_open_days)
        if waited > attempts:
            return "pending_enter:max_wait_open_days"

        drift_reason = self._pending_drift_abort_reason(as_of, bar)
        if drift_reason:
            return drift_reason
        return None

    def _abort_enter(self, as_of: str, reason: str) -> None:
        """放弃进场 → COMPLETE（无 entry）。"""
        self.lifecycle = Lifecycle.COMPLETE
        self.exit_info = ExitState(
            date=str(as_of or "").strip(),
            reason=str(reason or "pending_enter:abort"),
            ratio=0.0,
        )

    def _pending_attempts_allowed(self, max_wait_open_days: int) -> int:
        """``0`` → 仅 1 次可成交日；``N>0`` → N 个交易日。"""
        n = int(max_wait_open_days)
        return 1 if n <= 0 else n

    def _pending_wait_open_days(self, as_of: str) -> int:
        """自 trigger 次一开市日起，到 as_of（含）已经历的交易日数。"""
        trigger = str(self.trigger_date or "").strip()
        as_of = str(as_of or "").strip()
        if not trigger or not as_of or as_of <= trigger:
            return 0
        dates = [str(d).strip() for d in (self.open_dates or ()) if str(d).strip()]
        if not dates:
            # 无日历时：至少算 1 个可成交日（as_of > trigger）
            return 1
        return sum(1 for d in dates if trigger < d <= as_of)

    def _pending_wait_exhausted(self, as_of: str) -> bool:
        if self.settings is None:
            return False
        policy = self.settings.simulation.risk_control.pending_enter
        waited = self._pending_wait_open_days(as_of)
        return waited >= self._pending_attempts_allowed(policy.max_wait_open_days)

    def _pending_drift_abort_reason(
        self, as_of: str, bar: Dict[str, Any]
    ) -> Optional[str]:
        if self.settings is None:
            return None
        policy = self.settings.simulation.risk_control.pending_enter
        if policy.max_entry_drift is None:
            return None
        trigger_px = float(self.trigger_price or 0.0)
        if trigger_px <= 0:
            return None
        model = str(self.settings.simulation.enter_price or "touch").strip().lower()
        if model in {"open", "close"}:
            return None
        if as_of <= str(self.trigger_date or "").strip():
            return None
        open_px = SafeBarValue.float(bar, "open")
        if open_px <= 0:
            return None
        drift = abs(open_px - trigger_px) / trigger_px
        if drift <= float(policy.max_entry_drift):
            return None
        # touch：若当日已触及限价，仍按限价成交，不因 open 跳空 abort
        if model == "touch" and self._touch_limit_hit(bar):
            return None
        return "pending_enter:max_entry_drift"

    def _touch_limit_hit(self, bar: Dict[str, Any]) -> bool:
        limit = float(self.trigger_price or 0.0)
        if limit <= 0:
            return False
        low = SafeBarValue.float(bar, "low")
        high = SafeBarValue.float(bar, "high")
        if low <= 0 or high <= 0:
            return False
        return low <= limit <= high

    def _stock_meta_dict(self) -> Dict[str, Any]:
        stock = self.stock
        if isinstance(stock, StockInfo):
            return {
                "id": stock.id,
                "delist_date": getattr(stock, "delist_date", "") or "",
                "delisted_date": getattr(stock, "delist_date", "") or "",
            }
        if isinstance(stock, dict):
            return dict(stock)
        return {}

    @staticmethod
    def _is_delisted_on(stock_meta: Optional[Dict[str, Any]], trade_date: str) -> bool:
        if not stock_meta or not trade_date:
            return False
        delist = str(
            stock_meta.get("delist_date")
            or stock_meta.get("delisted_date")
            or ""
        ).strip()
        if not delist:
            return False
        return trade_date >= delist

    def _apply_enter(self, as_of: str, bar: Dict[str, Any]) -> None:
        price = self._resolve_entry_price(as_of, bar)
        if price is None:
            return
        raw_price = self._resolve_entry_price(as_of, bar, use_raw=True)
        at_limit_up, prev_close = self._eval_limit_up(price, bar)
        self.entry = EnterState(
            price=price,
            price_raw=float(raw_price or 0.0),
            date=str(as_of or "").strip(),
            direction=TradeSide.BUY,
            prev_close=prev_close,
            at_limit=at_limit_up,
            bar_volume=SafeBarValue.volume(bar),
        )

    def _resolve_entry_price(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        use_raw: bool = False,
        check_tradability: bool = True,
    ) -> Optional[float]:
        """Entry fill price for this tick, or ``None`` if not ready / blocked.

        ``enter_price``: ``next_open`` | ``touch`` | ``open`` | ``close``。
        ``touch``：限价=``trigger_price``，当日 high/low 触及则成交。
        """
        if self.lifecycle != Lifecycle.PENDING_TO_ENTER:
            return None

        trigger = str(self.trigger_date or "").strip()
        as_of = str(as_of or "").strip()
        if not trigger or not as_of:
            return None

        model = str(self.settings.simulation.enter_price or "touch").strip().lower()
        if model == "next_open":
            if as_of <= trigger:
                return None
            price = SafeBarValue.price_for_model(bar, "open", use_raw=use_raw)
        elif model == "touch":
            if as_of <= trigger:
                return None
            if not self._touch_limit_hit(bar):
                return None
            limit = float(self.trigger_price or 0.0)
            if limit <= 0:
                return None
            if use_raw:
                # 无独立 raw trigger 时用同一限价
                price = limit
            else:
                price = limit
        elif model in {"close", "open"}:
            if as_of != trigger:
                return None
            price = SafeBarValue.price_for_model(bar, model, use_raw=use_raw)
        else:
            raise ValueError(f"unsupported enter_price: {model!r}")

        if price <= 0:
            return None
        if (
            check_tradability
            and not use_raw
            and self._is_enter_blocked_by_limit_up(price, bar)
        ):
            return None
        return self.settings.simulation.tradability.slippage.apply_enter(price)

    def _is_able_to_exit(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        price_model: Optional[str] = None,
        check_tradability: bool = True,
    ) -> bool:
        """Whether this tick can fill exit per ``exit_price`` (no mutation)."""
        fill_as_of, fill_bar = self._resolve_exit_fill(as_of, bar)
        return (
            self._resolve_exit_price(
                fill_as_of,
                fill_bar,
                price_model=price_model,
                check_tradability=check_tradability,
            )
            is not None
        )

    def _apply_exit(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        price_model: Optional[str] = None,
        check_tradability: bool = True,
    ) -> bool:
        """Record exit leg from ``pending_exit``. Returns ``True`` if fill applied."""
        fill_as_of, fill_bar = self._resolve_exit_fill(as_of, bar)
        exit_price = self._resolve_exit_price(
            fill_as_of,
            fill_bar,
            price_model=price_model,
            check_tradability=check_tradability,
        )
        if exit_price is None or self.pending_exit is None:
            return False

        # pending.exit_ratio = 相对剩余仓位；记入 completed_goals 用相对初始份额
        relative = float(self.pending_exit.exit_ratio or 1.0)
        if relative <= 0:
            return False
        prev_remaining = float(self.runtime_state.remaining_ratio or 0.0)
        if prev_remaining <= 1e-12:
            return False
        abs_ratio = prev_remaining * min(relative, 1.0)
        new_remaining = max(0.0, prev_remaining - abs_ratio)
        self.runtime_state.remaining_ratio = new_remaining

        basis = float(self.entry.price or self.trigger_price or 0.0)
        profit = exit_price - basis
        roi = (profit / basis) if basis > 0 else 0.0
        exit_price_raw = self._resolve_exit_price(
            fill_as_of,
            fill_bar,
            price_model=price_model,
            use_raw=True,
            check_tradability=False,
        )
        at_limit_down, exit_prev_close = self._eval_limit_down(exit_price, fill_bar)

        self.completed_goals.append(
            {
                "name": self.pending_exit.goal_name or self.pending_exit.reason,
                "date": fill_as_of,
                "price": exit_price,
                "price_raw": float(exit_price_raw or 0.0),
                "exit_ratio": abs_ratio,
                "profit": profit,
                "weighted_profit": profit * abs_ratio,
                "reason": self.pending_exit.reason,
                "roi": roi,
            }
        )

        prev_weighted = float(self.outcome.weighted_roi or 0.0)
        self.outcome.weighted_roi = prev_weighted + roi * abs_ratio
        self.outcome.price_return = roi

        if new_remaining <= 1e-12:
            total_abs = sum(
                float(g.get("exit_ratio") or 0.0) for g in self.completed_goals
            )
            self.exit_info = ExitState(
                price=exit_price,
                price_raw=float(exit_price_raw or 0.0),
                date=fill_as_of,
                reason=self.pending_exit.reason,
                ratio=total_abs if total_abs > 0 else abs_ratio,
                prev_close=exit_prev_close,
                at_limit=at_limit_down,
                bar_volume=SafeBarValue.volume(fill_bar),
            )
            self.outcome.result = (
                InvestmentResult.WIN
                if float(self.outcome.weighted_roi or 0.0) >= 0
                else InvestmentResult.LOSS
            )
            entry_date = str(self.entry.date or "").strip()
            if entry_date and int(self.holding.days or 0) <= 0:
                mode = self.holding.mode or ExpirationMode.OPEN_DAY
                self.holding.days = self._holding_days(
                    entry_date, fill_as_of, mode, self.open_dates
                )
                self.holding.last_bar_date = fill_as_of
        self.pending_exit = None
        return True

    def _resolve_exit_fill(
        self,
        as_of: str,
        bar: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """退市 ``fill_bar`` 覆盖成交日 / 定价 bar。"""
        pending = self.pending_exit
        if pending is not None and isinstance(pending.fill_bar, dict) and pending.fill_bar:
            fill = pending.fill_bar
            day = str(fill.get("date") or "").strip()
            return (day or as_of, fill)
        return as_of, bar

    def _resolve_exit_price(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        price_model: Optional[str] = None,
        use_raw: bool = False,
        check_tradability: bool = True,
    ) -> Optional[float]:
        """Exit fill price for this tick, or ``None`` if not ready / blocked."""
        if self.pending_exit is None:
            return None
        if self.lifecycle not in (Lifecycle.OPEN, Lifecycle.PENDING_TO_EXIT):
            return None

        pending = self.pending_exit
        kind = str(pending.kind or "").strip().lower()
        if kind == PendingExitKind.NEXT_OPEN_DEFER.value:
            armed = str(pending.armed_as_of or "").strip()
            day = str(as_of or "").strip()
            if armed and day and day <= armed:
                return None

        if price_model is not None:
            model = str(price_model).strip().lower()
        elif self.lifecycle == Lifecycle.PENDING_TO_EXIT:
            model = self._pending_exit_fill_model()
        else:
            model = str(self.settings.simulation.exit_price or "close").strip().lower()

        exit_price = SafeBarValue.price_for_model(bar, model, use_raw=use_raw)
        if exit_price <= 0:
            return None
        if (
            check_tradability
            and not use_raw
            and self._is_exit_blocked_by_limit_down(exit_price, bar)
        ):
            return None
        return self.settings.simulation.tradability.slippage.apply_exit(exit_price)

    def settle(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """Force-close at simulate end. Returns ``False`` (stop tracking).

        ``PENDING_TO_ENTER`` + ``enter_price=next_open`` 且再无下一 tick 时：
        - ``no_next_tick=skip_trade``：放弃进场（COMPLETE，无成交）
        - ``no_next_tick=use_last_close``：用信号日 close 进场，再按模拟结束强平
        """
        if self.lifecycle == Lifecycle.COMPLETE:
            return False
        as_of = str(as_of or "").strip()
        if self.lifecycle == Lifecycle.PENDING_TO_ENTER:
            if not self._apply_no_next_tick_enter(as_of, bar):
                self.lifecycle = Lifecycle.COMPLETE
                return False
        self.pending_exit = PendingExit(
            reason=ExitReason.SIMULATE_END.value,
            exit_ratio=1.0,
            goal_name="simulate_end",
        )
        if self.lifecycle in (Lifecycle.OPEN, Lifecycle.PENDING_TO_EXIT):
            # 强平不受贴板政策拦截
            self._apply_exit(
                as_of,
                bar,
                price_model="close",
                check_tradability=False,
            )
        self.lifecycle = Lifecycle.COMPLETE
        return False

    def _apply_no_next_tick_enter(self, as_of: str, bar: Dict[str, Any]) -> bool:
        """样本末尾处理挂起的 ``next_open`` 进场。成功则进入 ``OPEN``。"""
        model = str(self.settings.simulation.enter_price or "touch").strip().lower()
        if model != "next_open":
            return False
        policy = str(self.settings.simulation.tradability.edges.no_next_tick or "skip_trade").strip().lower()
        if policy != "use_last_close":
            return False

        signal_bar = self.record_of_today if isinstance(self.record_of_today, dict) else None
        if not signal_bar:
            signal_bar = bar if isinstance(bar, dict) else {}
        fill_as_of = str(
            (signal_bar.get("date") if isinstance(signal_bar, dict) else None)
            or as_of
            or self.trigger_date
            or ""
        ).strip()
        price = SafeBarValue.price_for_model(signal_bar, "close", use_raw=False)
        if price <= 0:
            return False
        at_limit_up, prev_close = self._eval_limit_up(price, signal_bar)
        price = self.settings.simulation.tradability.slippage.apply_enter(price)
        raw_price = SafeBarValue.price_for_model(signal_bar, "close", use_raw=True)
        if raw_price > 0:
            raw_price = self.settings.simulation.tradability.slippage.apply_enter(raw_price)
        self.entry = EnterState(
            price=price,
            price_raw=float(raw_price or 0.0),
            date=fill_as_of,
            direction=TradeSide.BUY,
            prev_close=prev_close,
            at_limit=at_limit_up,
            bar_volume=SafeBarValue.volume(signal_bar),
        )
        self.lifecycle = Lifecycle.OPEN
        self._update_extremes(fill_as_of, signal_bar)
        self._remember_bar(signal_bar)
        return True

    def _entity_id(self) -> str:
        stock = self.stock
        if isinstance(stock, StockInfo):
            return str(stock.id or "").strip()
        if isinstance(stock, dict):
            return str(stock.get("id") or "").strip()
        return ""

    def _status_tags(self, bar: Dict[str, Any]) -> Tuple[str, ...]:
        """成交日 status tags（ST 等）；无 provider 或无法解析日期时为空。"""
        provider = self.status_tags_provider
        if provider is None:
            return ()
        trade_date = str(bar.get("date") or "").strip()
        entity_id = self._entity_id()
        if not trade_date or not entity_id:
            return ()
        tags = provider.status_tags_at(entity_id, trade_date)
        if not tags:
            return ()
        return tuple(str(t) for t in tags)

    def _eval_limit_up(
        self, price: float, bar: Dict[str, Any]
    ) -> Tuple[Optional[bool], Optional[float]]:
        """返回 ``(是否贴涨停, prev_close)``；无法判断时 flag 为 None。"""
        prev = SafeBarValue.optional_float(bar, "pre_close")
        entity_id = self._entity_id()
        if prev is None or prev <= 0 or not entity_id:
            return None, (prev if prev is not None and prev > 0 else None)
        return (
            bool(
                self.market_rules.is_at_limit_up(
                    price,
                    prev,
                    entity_id,
                    status_tags=self._status_tags(bar),
                )
            ),
            float(prev),
        )

    def _eval_limit_down(
        self, price: float, bar: Dict[str, Any]
    ) -> Tuple[Optional[bool], Optional[float]]:
        """返回 ``(是否贴跌停, prev_close)``；无法判断时 flag 为 None。"""
        prev = SafeBarValue.optional_float(bar, "pre_close")
        entity_id = self._entity_id()
        if prev is None or prev <= 0 or not entity_id:
            return None, (prev if prev is not None and prev > 0 else None)
        return (
            bool(
                self.market_rules.is_at_limit_down(
                    price,
                    prev,
                    entity_id,
                    status_tags=self._status_tags(bar),
                )
            ),
            float(prev),
        )

    def _is_enter_blocked_by_limit_up(self, price: float, bar: Dict[str, Any]) -> bool:
        """贴涨停且 settings 不允许进场 → True（本 tick 不成交）。"""
        if self.settings.simulation.allow_enter_at_limit_up:
            return False
        at_limit, _ = self._eval_limit_up(price, bar)
        return bool(at_limit)

    def _is_exit_blocked_by_limit_down(self, price: float, bar: Dict[str, Any]) -> bool:
        """贴跌停且 settings 不允许出场 → True（本 tick 不成交）。"""
        if self.settings.simulation.allow_exit_at_limit_down:
            return False
        at_limit, _ = self._eval_limit_down(price, bar)
        return bool(at_limit)

    def _update_extremes(self, as_of: str, bar: Dict[str, Any]) -> None:
        if self.lifecycle != Lifecycle.OPEN:
            return
        basis = float(self.entry.price or 0.0)
        if basis <= 0:
            return
        high = float(bar.get("high") or bar.get("close") or 0.0)
        low = float(bar.get("low") or bar.get("close") or 0.0)
        if high <= 0 or low <= 0:
            return
        if self.extreme.highest is None or high > self.extreme.highest:
            self.extreme.highest = high
            self.extreme.highest_date = as_of
            self.extreme.highest_return = (high - basis) / basis
        if self.extreme.lowest is None or low < self.extreme.lowest:
            self.extreme.lowest = low
            self.extreme.lowest_date = as_of
            self.extreme.lowest_return = (low - basis) / basis

    def _update_holding(self, as_of: str) -> None:
        if self.lifecycle != Lifecycle.OPEN or self.holding.mode is None:
            return
        entry_date = str(self.entry.date or "").strip()
        if not entry_date:
            return
        self.holding.days = self._holding_days(
            entry_date, as_of, self.holding.mode, self.open_dates
        )
        self.holding.last_bar_date = as_of
        self.holding.counter_initialized = True

    @staticmethod
    def _copy_dataclass(value: Any, cls: type) -> Any:
        if isinstance(value, cls):
            return cls(**{f.name: getattr(value, f.name) for f in fields(cls)})
        if isinstance(value, dict):
            return cls(**{f.name: value.get(f.name, "") for f in fields(cls)})
        return cls()

    @staticmethod
    def _open_days_inclusive(start_date: str, end_date: str, open_dates: Sequence[str]) -> int:
        start = str(start_date).strip()
        end = str(end_date).strip()
        if not start or not end or not open_dates:
            return 0
        if start > end:
            return 0
        start_idx = bisect_left(open_dates, start)
        end_idx = bisect_left(open_dates, end)
        if start_idx >= len(open_dates) or open_dates[start_idx] != start:
            return 0
        if end_idx >= len(open_dates) or open_dates[end_idx] != end:
            return 0
        return end_idx - start_idx + 1

    @classmethod
    def _settlement_days_held(cls, entry_date: str, as_of: str, open_dates: Sequence[str]) -> int:
        """Trading days held for settlement (entry day does not count toward T+N)."""
        inclusive = cls._open_days_inclusive(entry_date, as_of, open_dates)
        return max(inclusive - 1, 0)

    @classmethod
    def _holding_days(
        cls,
        entry_date: str,
        as_of: str,
        mode: ExpirationMode,
        open_dates: Sequence[str],
    ) -> int:
        if mode in (ExpirationMode.OPEN_DAY, ExpirationMode.TRADING_DAY):
            return cls._open_days_inclusive(entry_date, as_of, open_dates)
        try:
            start_dt = datetime.strptime(str(entry_date).strip(), "%Y%m%d")
            end_dt = datetime.strptime(str(as_of).strip(), "%Y%m%d")
            return max((end_dt - start_dt).days, 0)
        except ValueError:
            return 0

    def to_opportunity(self) -> Opportunity:
        """投影为 Opportunity，剥离 lifecycle / entry / exit / goals / outcome 等结果字段。

        供 ``on_pick_portfolio_member`` 等用户钩子使用，避免用结果数据作弊选仓。
        """
        return Opportunity(
            stock=StockInfo.from_dict(self.stock.to_dict()),
            record_of_today=dict(self.record_of_today or {}),
            trigger_date=str(self.trigger_date or ""),
            trigger_price=float(self.trigger_price or 0.0),
            trigger_price_raw=float(self.trigger_price_raw or 0.0),
            market_profile=str(self.market_profile or ""),
            meta=self._copy_dataclass(self.meta, OpportunityMeta),
            contributor=self._copy_dataclass(self.contributor, OpportunityContributor),
            extra_fields=dict(self.extra_fields or {}),
            metadata=dict(self.metadata or {}),
        )



__all__ = [
    "Investment",
]
