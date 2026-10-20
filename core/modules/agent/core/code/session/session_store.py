"""会话落盘：全文记录、局部任务状态、跨会话偏好。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.modules.agent.core.code.conf.conf import (
    DEFAULT_SESSION_ID,
    SESSION_ARCHIVE_AFTER,
    SESSION_KEEP_ACTIVE,
    SESSION_RECENT_TURNS,
)

_SESSION_ID = re.compile(r"^[a-zA-Z0-9_]{1,64}$")


def default_session_id() -> str:
    return DEFAULT_SESSION_ID


def agent_root() -> Path:
    return ProjectContext.path.get_userspace_ntq_directory() / "agent"


def preferences_path() -> Path:
    return agent_root() / "preferences.json"


def sessions_root() -> Path:
    return agent_root() / "sessions"


def session_directory(session_id: str = DEFAULT_SESSION_ID) -> Path:
    sid = _parse_session_id(session_id)
    path = sessions_root() / sid
    path.mkdir(parents=True, exist_ok=True)
    (path / "archive").mkdir(parents=True, exist_ok=True)
    return path


def load_preferences() -> List[str]:
    path = preferences_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = raw.get("rules") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def save_preferences(rules: List[str]) -> None:
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned: List[str] = []
    for item in rules:
        text = str(item or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
    path.write_text(
        json.dumps({"rules": cleaned}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def remember_preference(rule: str) -> List[str]:
    text = str(rule or "").strip()
    rules = load_preferences()
    if text and text not in rules:
        rules.append(text)
        save_preferences(rules)
    return rules


def forget_preference(rule: str) -> List[str]:
    text = str(rule or "").strip()
    rules = [item for item in load_preferences() if item != text]
    save_preferences(rules)
    return rules


def load_state(session_id: str = DEFAULT_SESSION_ID) -> Dict[str, Any]:
    path = session_directory(session_id) / "state.json"
    if not path.is_file():
        return _empty_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()
    if not isinstance(raw, dict):
        return _empty_state()
    state = _empty_state()
    state["strategy_key"] = str(raw.get("strategy_key") or "").strip()
    last = raw.get("last_task")
    if isinstance(last, dict):
        state["last_task"] = {
            "task_id": str(last.get("task_id") or "").strip(),
            "kind": str(last.get("kind") or "").strip(),
            "status": str(last.get("status") or "").strip(),
        }
    facts = raw.get("facts")
    if isinstance(facts, dict):
        state["facts"] = {
            str(k): v for k, v in facts.items() if str(k).strip() and v is not None
        }
    state["pending"] = str(raw.get("pending") or "").strip()
    return state


def save_state(state: Dict[str, Any], session_id: str = DEFAULT_SESSION_ID) -> None:
    path = session_directory(session_id) / "state.json"
    payload = {
        "strategy_key": str(state.get("strategy_key") or "").strip(),
        "last_task": state.get("last_task")
        if isinstance(state.get("last_task"), dict)
        else {},
        "facts": state.get("facts") if isinstance(state.get("facts"), dict) else {},
        "pending": str(state.get("pending") or "").strip(),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def append_turn(
    *,
    user: str,
    reply: str,
    channel: str,
    handoff: bool,
    session_id: str = DEFAULT_SESSION_ID,
) -> None:
    directory = session_directory(session_id)
    path = directory / "transcript.jsonl"
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": str(user or "").strip(),
        "reply": str(reply or "").strip(),
        "channel": str(channel or "").strip(),
        "handoff": bool(handoff),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    _maybe_archive(directory)


def recent_turns(
    session_id: str = DEFAULT_SESSION_ID, *, limit: int = SESSION_RECENT_TURNS
) -> List[Dict[str, str]]:
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
    out: List[Dict[str, str]] = []
    for item in rows[-max(1, int(limit)) :]:
        user = str(item.get("user") or "").strip()
        reply = str(item.get("reply") or "").strip()
        if user:
            out.append({"role": "user", "content": user})
        if reply:
            out.append({"role": "assistant", "content": reply})
    return out


def context_block(session_id: str = DEFAULT_SESSION_ID) -> str:
    """拼一段给模型看的短上下文：偏好 + 当前任务状态。"""
    lines: List[str] = []
    prefs = load_preferences()
    if prefs:
        lines.append("用户长期偏好：")
        for rule in prefs:
            lines.append(f"- {rule}")
    state = load_state(session_id)
    bits: List[str] = []
    if state.get("strategy_key"):
        bits.append(f"当前策略：{state['strategy_key']}")
    last = state.get("last_task") if isinstance(state.get("last_task"), dict) else {}
    if last.get("task_id"):
        bits.append(
            "最近任务："
            f"{last.get('kind') or '?'} {last.get('task_id')} "
            f"({last.get('status') or '?'})"
        )
    facts = state.get("facts") if isinstance(state.get("facts"), dict) else {}
    if facts:
        bits.append("已告知用户的数字：" + json.dumps(facts, ensure_ascii=False))
    if state.get("pending"):
        bits.append(f"待确认：{state['pending']}")
    if bits:
        if lines:
            lines.append("")
        lines.append("当前任务状态：")
        lines.extend(f"- {item}" for item in bits)
    return "\n".join(lines).strip()


def update_state_from_tool(
    result: Dict[str, Any], session_id: str = DEFAULT_SESSION_ID
) -> Dict[str, Any]:
    """用工具摘要刷新局部状态。不写偏好。"""
    state = load_state(session_id)
    if not isinstance(result, dict):
        return state
    key = str(result.get("key") or "").strip()
    if key:
        state["strategy_key"] = key
    task_id = str(result.get("task_id") or "").strip()
    if task_id:
        state["last_task"] = {
            "task_id": task_id,
            "kind": str(result.get("kind") or "").strip(),
            "status": str(result.get("status") or "").strip(),
        }
    facts = dict(state.get("facts") or {})
    for name in (
        "total_return",
        "max_drawdown",
        "win_rate",
        "total_trades",
        "total_opportunities",
        "hit_stocks",
        "date",
        "version_id",
        "group_id",
    ):
        if name in result and result.get(name) not in (None, ""):
            facts[name] = result.get(name)
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    for name, value in summary.items():
        if value not in (None, "") and name in {
            "total_return",
            "max_drawdown",
            "win_rate",
            "total_trades",
            "total_opportunities",
            "trigger_stocks",
            "trigger_ratio",
        }:
            facts[name] = value
    nested = result.get("result") if isinstance(result.get("result"), dict) else {}
    for name in (
        "total_opportunities",
        "hit_stocks",
        "date",
        "at_limit_up_count",
        "universe",
    ):
        if nested.get(name) not in (None, ""):
            facts[name] = nested.get(name)
    state["facts"] = facts
    save_state(state, session_id)
    return state


def clear_session(session_id: str = DEFAULT_SESSION_ID) -> None:
    """清空会话对话与局部状态。不碰跨会话偏好和策略产物。"""
    directory = session_directory(session_id)
    transcript = directory / "transcript.jsonl"
    if transcript.is_file():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = directory / "archive" / f"transcript-{stamp}.jsonl"
        transcript.replace(archive)
    save_state(_empty_state(), session_id)


def _empty_state() -> Dict[str, Any]:
    return {
        "strategy_key": "",
        "last_task": {},
        "facts": {},
        "pending": "",
    }


def _parse_session_id(session_id: str) -> str:
    sid = str(session_id or "").strip() or DEFAULT_SESSION_ID
    if not _SESSION_ID.fullmatch(sid):
        raise ValueError("session_id 无效")
    return sid


def _maybe_archive(directory: Path) -> None:
    path = directory / "transcript.jsonl"
    if not path.is_file():
        return
    try:
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        return
    if len(lines) <= SESSION_ARCHIVE_AFTER:
        return
    keep = lines[-SESSION_KEEP_ACTIVE:]
    old = lines[:-SESSION_KEEP_ACTIVE]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = directory / "archive" / f"transcript-{stamp}.jsonl"
    try:
        with archive.open("a", encoding="utf-8") as handle:
            for line in old:
                handle.write(line + "\n")
        path.write_text("\n".join(keep) + "\n", encoding="utf-8")
    except OSError:
        return


__all__ = [
    "append_turn",
    "clear_session",
    "context_block",
    "default_session_id",
    "forget_preference",
    "load_preferences",
    "load_state",
    "recent_turns",
    "remember_preference",
    "save_preferences",
    "save_state",
    "session_directory",
    "update_state_from_tool",
]
