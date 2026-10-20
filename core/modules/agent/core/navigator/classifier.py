"""Navigator 分类：输出有序意图清单（先执行头一个，其余可引导确认）。"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Sequence

from core.infra.ai import AiChannel
from core.infra.ai.contracts import AiError

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

_SYSTEM = """你是 NTQ 对话分流器。根据用户一句话，只输出一个 JSON，不要其它字：
{"kinds":["...", "..."]}

kinds 是有序清单：按「先执行谁」排列。系统会先做第 1 项（含拒绝），做完再询问是否继续第 2 项。
若只有一个意图，kinds 长度为 1。不要输出空数组。

可选 kind：
- advice：索取投资建议、荐股、「什么策略赚钱/稳赚/该买什么」、要你推荐能赚钱的策略（红线）
- out_of_scope：外网新闻、时事暴乱、美联储/宏观、实时行情、泛投资热点（红线）
- guide_arch：框架架构、设计原理、目录分层、userspace 隔离（不要求动手）
- identity：短问 NTQ/新茶/New Tea Quant 是什么、简介、全称
- guide：用法、读报告、说明书、配置含义、排障思路、闲聊续聊；问怎么配/怎么读但未要求立刻动手
- worker：写/改策略、回测、扫描、归因、复查、重跑、校验等动手任务

清单排序规则（必须遵守）：
1. 若含投资建议陷阱 → advice 必须在最前；若同时还要求写策略/回测，可再挂 worker（勿把 worker 放 advice 前）
2. 若含外网/宏观资讯 → out_of_scope 靠前；若同时还要求改策略/回测，可再挂 worker
3. 品牌介绍 + 顺便做事 → identity（或 guide_arch）在前，worker 在后
4. 纯做事 → 仅 ["worker"]
5. 纯说明书/读报告 → 仅 ["guide"] 或 ["guide_arch"]
"""


def classify_route(
    text: str,
    *,
    ntq_mode: str = "ask",
    provider_id: str = "ntq",
) -> Optional[List[str]]:
    """返回有序 kinds；失败返回 None（由调用方正则兜底）。

    ``ntq_mode`` is retained for eval_gate callers; live NTQ uses
    ``extra_body.ntq.phase=navigate``.
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
            # Navigator step of the 1×navigate → 0…N×act chain.
            extra = {
                "ntq": {"phase": "navigate", "intent": None},
                "ntq_mode": "work",  # legacy: heavy lane
            }
        result = AiChannel.complete(
            [
                {"role": "system", "content": _SYSTEM},
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
            raw_list = payload.get("kinds")
            if raw_list is None and payload.get("kind"):
                raw_list = [payload.get("kind")]
            normalized = _normalize_kinds(raw_list)
            if normalized:
                return normalized
    # 兜底：正文里扫到的 kind，再按 pipeline 排序
    found = [k for k in _PIPELINE_RANK if re.search(rf"\b{k}\b", body)]
    if found:
        return sort_pipeline(found)
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
