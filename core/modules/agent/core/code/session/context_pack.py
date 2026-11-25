"""分层 context 打包：固定状态 + 会话摘要 + 近期原文 + 本轮工具清扫。

LLM compaction 由本机编排；走现有 Provider 补全（ntq 时官网计费）。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.agent.core.code.conf.conf import (
    COMPACT_CHAR_THRESHOLD,
    COMPACT_MAX_TOKENS,
    COMPACT_MSG_THRESHOLD,
    COMPACT_SUMMARY_MAX_CHARS,
    PRODUCT_PROVIDER_ID,
    SESSION_DIGEST_REPLY_CHARS,
    SESSION_DIGEST_TURNS,
    SESSION_DIGEST_USER_CHARS,
    SESSION_VERBATIM_TURNS,
    TOOL_RESULT_MSG_MAX_CHARS,
    WORKING_KEEP_TOOL_PAIRS,
)
from core.modules.agent.core.code.session.session_store import (
    context_block,
    session_directory,
)

logger = logging.getLogger(__name__)

_TOOL_RESULT_PREFIX = "工具结果："
_DONE_TOOLS_PREFIX = "已完成工具："


def compact_summary_path(session_id: str) -> Path:
    return session_directory(session_id) / "compact_summary.md"


def load_compact_summary(session_id: str) -> str:
    path = compact_summary_path(session_id)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def save_compact_summary(session_id: str, text: str) -> None:
    body = str(text or "").strip()
    if len(body) > COMPACT_SUMMARY_MAX_CHARS:
        body = body[:COMPACT_SUMMARY_MAX_CHARS].rstrip() + "…"
    path = compact_summary_path(session_id)
    path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def load_transcript_rows(session_id: str) -> List[Dict[str, Any]]:
    path = session_directory(session_id) / "transcript.jsonl"
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    except OSError:
        return []
    return rows


def build_session_memory(
    session_id: str,
    *,
    verbatim_turns: int = SESSION_VERBATIM_TURNS,
    digest_turns: int = SESSION_DIGEST_TURNS,
) -> List[Dict[str, str]]:
    """B 会话摘要 + C 近期原文（不含 preamble/context_block）。"""
    rows = load_transcript_rows(session_id)
    if not rows:
        summary = load_compact_summary(session_id)
        if summary:
            return [
                {
                    "role": "system",
                    "content": "会话压缩摘要：\n" + summary,
                }
            ]
        return []

    v = max(0, int(verbatim_turns))
    d = max(0, int(digest_turns))
    verbatim = rows[-v:] if v else []
    older = rows[: -v] if v else rows
    if d and older:
        older = older[-d:]
    else:
        older = []

    out: List[Dict[str, str]] = []
    llm_summary = load_compact_summary(session_id)
    if llm_summary:
        out.append(
            {
                "role": "system",
                "content": "会话压缩摘要：\n" + llm_summary,
            }
        )
    elif older:
        digest = _extractive_digest(older)
        if digest:
            out.append(
                {
                    "role": "system",
                    "content": "更早对话摘要（抽取）：\n" + digest,
                }
            )

    for item in verbatim:
        user = str(item.get("user") or "").strip()
        reply = str(item.get("reply") or "").strip()
        if user:
            out.append({"role": "user", "content": user})
        if reply:
            out.append({"role": "assistant", "content": reply})
    return out


def clip_tool_result_content(content: str) -> str:
    text = str(content or "")
    limit = max(500, int(TOOL_RESULT_MSG_MAX_CHARS))
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n…(工具结果已截断)"


def compact_working_messages(
    messages: Sequence[Dict[str, str]],
    *,
    keep_tool_pairs: int = WORKING_KEEP_TOOL_PAIRS,
) -> List[Dict[str, str]]:
    """清扫本轮工具往返：保留 system 头 + 首个本轮 user + 最近 K 对工具。"""
    rows = [dict(m) for m in messages if isinstance(m, dict)]
    if not rows:
        return []

    head: List[Dict[str, str]] = []
    i = 0
    while i < len(rows) and str(rows[i].get("role") or "") == "system":
        head.append(rows[i])
        i += 1

    rest = rows[i:]
    if not rest:
        return head

    # 第一个非 system user 视为本轮用户原话（其后才是工具环）
    anchor_idx = 0
    for j, item in enumerate(rest):
        if str(item.get("role") or "") == "user" and not _is_tool_or_nudge(
            str(item.get("content") or "")
        ):
            anchor_idx = j
            break
    prefix = rest[: anchor_idx + 1]
    tail = rest[anchor_idx + 1 :]

    pairs, leftover = _split_pairs(tail)
    keep = max(0, int(keep_tool_pairs))
    dropped = pairs[:-keep] if keep and len(pairs) > keep else pairs[:0]
    kept = pairs[-keep:] if keep else []

    out = list(head) + list(prefix)
    if dropped:
        names = _tool_names_from_pairs(dropped)
        note = _DONE_TOOLS_PREFIX + (
            ", ".join(names) if names else f"{len(dropped)} 步"
        )
        note += "（细节见任务状态/可再查报告；勿重复无意义调用）"
        out.append({"role": "user", "content": note})
    for pair in kept:
        out.extend(pair)
    out.extend(leftover)

    # 截断仍在场的工具结果
    for item in out:
        if str(item.get("role") or "") != "user":
            continue
        content = str(item.get("content") or "")
        if content.startswith(_TOOL_RESULT_PREFIX):
            item["content"] = clip_tool_result_content(content)
    return out


def messages_over_budget(
    messages: Sequence[Dict[str, str]],
    *,
    msg_threshold: int = COMPACT_MSG_THRESHOLD,
    char_threshold: int = COMPACT_CHAR_THRESHOLD,
) -> bool:
    rows = [m for m in messages if isinstance(m, dict)]
    if len(rows) >= max(1, int(msg_threshold)):
        return True
    total = sum(len(str(m.get("content") or "")) for m in rows)
    return total >= max(1000, int(char_threshold))


def should_llm_compact(session_id: str, *, force: bool = False) -> bool:
    """是否值得打一次 LLM 会话摘要。"""
    if force:
        return True
    rows = load_transcript_rows(session_id)
    older_n = max(0, len(rows) - max(0, int(SESSION_VERBATIM_TURNS)))
    if older_n < 4:
        return False
    # 尚无落盘摘要，或更早轮次已经很多
    if not load_compact_summary(session_id):
        return True
    return older_n > int(SESSION_DIGEST_TURNS)


def maybe_llm_compact(
    session_id: str,
    *,
    provider_id: str,
    billing: Optional[Dict[str, Any]] = None,
    force: bool = False,
) -> bool:
    """用模型写会话摘要并落盘；失败返回 False（不阻断主对话）。"""
    if not should_llm_compact(session_id, force=force):
        return False
    rows = load_transcript_rows(session_id)
    block = context_block(session_id)
    older = rows[: -SESSION_VERBATIM_TURNS] if SESSION_VERBATIM_TURNS else rows
    digest_src = _extractive_digest(older)
    if not digest_src and not block:
        return False

    try:
        from core.modules.agent.core.code.executor.shared.complete import ask
        from core.modules.agent.core.code.executor.shared.prompt_loader import (
            load_prompt,
        )
    except Exception:  # noqa: BLE001
        logger.exception("llm compact import failed")
        return False

    system = load_prompt("specific/context/compact_system.md").rstrip()
    user = load_prompt(
        "specific/context/compact_user.md",
        variables={
            "state": block or "（无）",
            "digest": digest_src or "（无）",
        },
    ).rstrip()
    try:
        summary = ask(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            provider_id=provider_id,
            max_tokens=COMPACT_MAX_TOKENS,
            ntq_phase="navigate" if provider_id == PRODUCT_PROVIDER_ID else "",
            ntq_intent=None,
            billing=billing,
        )
    except Exception:  # noqa: BLE001 — 压缩失败不挡主流程
        logger.exception("llm compact ask failed")
        return False
    text = str(summary or "").strip()
    if not text:
        return False
    save_compact_summary(session_id, text)
    return True


def _extractive_digest(rows: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    u_lim = max(20, int(SESSION_DIGEST_USER_CHARS))
    r_lim = max(20, int(SESSION_DIGEST_REPLY_CHARS))
    for item in rows:
        user = _one_line(str(item.get("user") or ""), u_lim)
        reply = _one_line(str(item.get("reply") or ""), r_lim)
        if not user and not reply:
            continue
        bit = "- "
        if user:
            bit += f"用户：{user}"
        if reply:
            bit += (" / " if user else "") + f"助手：{reply}"
        lines.append(bit)
    return "\n".join(lines).strip()


def _one_line(text: str, limit: int) -> str:
    s = re.sub(r"\s+", " ", str(text or "").strip())
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"


def _is_tool_or_nudge(content: str) -> bool:
    c = str(content or "")
    if c.startswith(_TOOL_RESULT_PREFIX) or c.startswith(_DONE_TOOLS_PREFIX):
        return True
    # nudges / heal prompts are synthetic user turns
    if c.startswith("工具") and "结果" in c[:20]:
        return True
    return False


def _split_pairs(
    tail: Sequence[Dict[str, str]],
) -> Tuple[List[List[Dict[str, str]]], List[Dict[str, str]]]:
    pairs: List[List[Dict[str, str]]] = []
    leftover: List[Dict[str, str]] = []
    i = 0
    items = list(tail)
    while i < len(items):
        a = items[i]
        if (
            i + 1 < len(items)
            and str(a.get("role") or "") == "assistant"
            and str(items[i + 1].get("role") or "") == "user"
        ):
            pairs.append([a, items[i + 1]])
            i += 2
            continue
        leftover.append(a)
        i += 1
    return pairs, leftover


def _tool_names_from_pairs(pairs: Sequence[Sequence[Dict[str, str]]]) -> List[str]:
    names: List[str] = []
    for pair in pairs:
        if len(pair) < 1:
            continue
        raw = str(pair[0].get("content") or "")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            tool = str(payload.get("tool") or "").strip()
            if tool:
                names.append(tool)
                continue
        # fallback: peek tool result user blob
        if len(pair) > 1:
            body = str(pair[1].get("content") or "")
            m = re.search(r'"tool"\s*:\s*"([^"]+)"', body)
            if m:
                names.append(m.group(1))
    # dedupe preserve order
    seen = set()
    out: List[str] = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out
