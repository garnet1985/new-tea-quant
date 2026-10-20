"""Navigator 分类：输出有序意图清单（先执行头一个，其余可引导确认）。"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Sequence

from core.infra.ai import AiChannel
from core.infra.ai.contracts import AiError
from core.modules.agent.core.prompt_store import load_prompt

logger = logging.getLogger(__name__)

ROUTE_KINDS = frozenset(
    {"identity", "advice", "out_of_scope", "guide_arch", "guide", "worker"}
)

# 清单排序：先处理红线/拒答/讲解，worker 常挂在末尾等用户确认
_PIPELINE_RANK = {
    "advice": 0,
    "out_of_scope": 1,
    "guide_arch": 2,
    "identity": 3,
    "guide": 4,
    "worker": 5,
}


def classify_route(
    text: str,
    *,
    provider_id: str = "ntq",
) -> Optional[List[str]]:
    """返回有序 kinds；失败返回 None（由调用方正则兜底）。

    Provider=ntq 时打 ``ntq.phase=navigate``（Website 只选分流模型，不替本地出意图）。
    """
    raw = str(text or "").strip()
    if not raw:
        return None
    pid = str(provider_id or "ntq").strip() or "ntq"
    # deepseek-flash（含 Website navigate 车道）会先占 reasoning_tokens；
    # 额度过小会出现 content 为空。
    max_tokens = 512 if pid in {"deepseek", "ntq"} else 128
    try:
        extra = None
        if pid == "ntq":
            extra = {"ntq": {"phase": "navigate", "intent": None}}
        result = AiChannel.complete(
            [
                {
                    "role": "system",
                    "content": load_prompt("navigate/classifier.md").rstrip(),
                },
                {"role": "user", "content": raw},
            ],
            provider_id=pid,
            max_tokens=max_tokens,
            temperature=0.0,
            extra_body=extra,
        )
        kinds = parse_kinds(result.reply)
        if kinds:
            return kinds
        logger.warning("router classifier bad reply: %s", (result.reply or "")[:160])
    except (AiError, OSError, TimeoutError, ValueError) as exc:
        logger.warning("router classifier failed: %s", exc)
    except Exception as exc:  # noqa: BLE001 — 分流失败必须可回退正则
        logger.warning("router classifier unexpected: %s", exc)
    return None


def parse_kinds(reply: str) -> Optional[List[str]]:
    body = str(reply or "").strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
    match = re.search(r"\{[^{}]*\}", body, flags=re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            normalized = _normalize_kinds(payload.get("kinds"))
            if normalized:
                return normalized
    return None


def sort_pipeline(kinds: Sequence[str]) -> List[str]:
    uniq: List[str] = []
    for kind in kinds:
        key = str(kind or "").strip()
        if key in ROUTE_KINDS and key not in uniq:
            uniq.append(key)
    uniq.sort(key=lambda k: _PIPELINE_RANK.get(k, 99))
    return uniq


def _normalize_kinds(raw_list: object) -> List[str]:
    if not isinstance(raw_list, list):
        return []
    cleaned: List[str] = []
    for item in raw_list:
        key = str(item or "").strip()
        if key in ROUTE_KINDS and key not in cleaned:
            cleaned.append(key)
    return sort_pipeline(cleaned) if cleaned else []
