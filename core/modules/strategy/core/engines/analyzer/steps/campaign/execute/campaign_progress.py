"""归因的多轮进度。每一轮回测是总进度里的一格。"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Optional, Sequence

from core.modules.backtest_engine.core.shared.progress import attach_round, phase_steps
from core.modules.strategy.core.enums import SimulateKind

from ..plan import AttributionTask

_CURRENT: ContextVar[Optional["CampaignProgress"]] = ContextVar(
    "attribute_campaign_progress", default=None
)

_STEP_LABEL = {
    SimulateKind.ENUMERATE: "枚举",
    SimulateKind.PRICE_FACTOR: "价格",
    SimulateKind.PORTFOLIO: "组合",
}


class CampaignProgress:
    """sea / spa / soa 共用一棵进度树。"""

    def __init__(self, root_id: str, slots: Sequence[str]) -> None:
        self.root_id = root_id
        self.slots = list(slots)
        self.cursor = 0
        self._token: Optional[Token[Optional["CampaignProgress"]]] = None

    @classmethod
    def open(
        cls,
        strategy_key: str,
        layer: str,
        tasks: Sequence[AttributionTask],
    ) -> Optional["CampaignProgress"]:
        slots: list[str] = []
        children: list[dict] = []
        root = _root_id(strategy_key, layer)
        index = 0
        for task in tasks:
            for step in tuple(task.steps) or (task.kind,):
                index += 1
                round_id = f"{root}:r{index}"
                label = _STEP_LABEL.get(step, str(step.value))
                children.append(
                    {
                        "id": round_id,
                        "label": f"第 {index} 轮 {label}",
                        "weight": 1,
                        "steps": phase_steps(round_id),
                    }
                )
                slots.append(round_id)
        if not slots:
            return None
        from core.infra.progress import Progress

        Progress.start(
            root,
            job="attribute",
            label=f"归因 {layer}",
            steps=children,
        )
        return cls(root, slots)

    def __enter__(self) -> "CampaignProgress":
        self._token = _CURRENT.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        from core.infra.progress import Progress

        try:
            if exc_type is None:
                Progress.finish(self.root_id)
            else:
                Progress.fail(self.root_id)
        except Exception:
            pass
        if self._token is not None:
            _CURRENT.reset(self._token)
            self._token = None

    @classmethod
    def current(cls) -> Optional["CampaignProgress"]:
        return _CURRENT.get()

    def skip(self, count: int) -> None:
        """这一轮没有真正开回测，直接记完成。"""
        from core.infra.progress import Progress

        for _ in range(max(0, int(count))):
            if self.cursor >= len(self.slots):
                return
            Progress.finish(self.slots[self.cursor])
            self.cursor += 1

    @contextmanager
    def bind(self) -> Iterator[str]:
        if self.cursor >= len(self.slots):
            yield ""
            return
        slot = self.slots[self.cursor]
        self.cursor += 1
        with attach_round(
            self.root_id,
            slot,
            index=self.cursor,
            total=len(self.slots),
        ):
            yield slot


def _root_id(strategy_key: str, layer: str) -> str:
    raw = f"attribute-{strategy_key}-{layer}"
    safe = raw.replace("/", "-").replace("\\", "-").replace("\x00", "").strip()
    return safe or "attribute"
