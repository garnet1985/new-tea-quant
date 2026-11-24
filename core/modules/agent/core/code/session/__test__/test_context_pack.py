"""分层 context 打包：digest / 工具清扫。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.agent.core.code.session import context_pack as cp


@pytest.fixture()
def session_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "sessions" / "default"
    root.mkdir(parents=True)

    def _dir(session_id: str = "default") -> Path:
        path = tmp_path / "sessions" / str(session_id or "default")
        path.mkdir(parents=True, exist_ok=True)
        (path / "archive").mkdir(exist_ok=True)
        return path

    monkeypatch.setattr(cp, "session_directory", _dir)
    import core.modules.agent.core.code.session.session_store as store

    monkeypatch.setattr(store, "session_directory", _dir)
    return root


def _write_transcript(session_dir: Path, n: int) -> None:
    path = session_dir / "transcript.jsonl"
    lines = []
    for i in range(n):
        lines.append(
            json.dumps(
                {"user": f"问题{i} " + ("详" * 40), "reply": f"回答{i} " + ("结" * 50)},
                ensure_ascii=False,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_build_session_memory_digest_and_verbatim(session_dir: Path) -> None:
    _write_transcript(session_dir, 10)
    mem = cp.build_session_memory("default", verbatim_turns=2, digest_turns=8)
    assert mem
    assert mem[0]["role"] == "system"
    assert "更早对话摘要" in mem[0]["content"] or "会话压缩摘要" in mem[0]["content"]
    # 2 turns → up to 4 messages after digest system
    roles = [m["role"] for m in mem[1:]]
    assert roles.count("user") == 2
    assert roles.count("assistant") == 2
    assert "问题8" in mem[-2]["content"] or "问题9" in "".join(
        m["content"] for m in mem if m["role"] == "user"
    )


def test_llm_summary_preferred_over_extractive(session_dir: Path) -> None:
    _write_transcript(session_dir, 8)
    cp.save_compact_summary("default", "用户要测均线策略，待确认回测计划。")
    mem = cp.build_session_memory("default", verbatim_turns=2, digest_turns=8)
    assert mem[0]["role"] == "system"
    assert "均线策略" in mem[0]["content"]
    assert "更早对话摘要（抽取）" not in mem[0]["content"]


def test_compact_working_keeps_last_tool_pairs() -> None:
    messages = [{"role": "system", "content": "sys"}]
    messages.append({"role": "user", "content": "帮我建策略"})
    for i in range(6):
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps({"tool": f"t{i}", "arguments": {}}, ensure_ascii=False),
            }
        )
        messages.append(
            {
                "role": "user",
                "content": "工具结果：\n" + json.dumps({"ok": True, "n": i}),
            }
        )
    out = cp.compact_working_messages(messages, keep_tool_pairs=2)
    assert out[0]["content"] == "sys"
    assert out[1]["content"] == "帮我建策略"
    assert any(str(m.get("content") or "").startswith("已完成工具：") for m in out)
    # last two pairs kept → 4 messages + maybe done note
    tool_results = [
        m for m in out if str(m.get("content") or "").startswith("工具结果：")
    ]
    assert len(tool_results) == 2


def test_clip_tool_result() -> None:
    big = "工具结果：\n" + ("x" * 20_000)
    clipped = cp.clip_tool_result_content(big)
    assert len(clipped) < len(big)
    assert "截断" in clipped


def test_messages_over_budget() -> None:
    small = [{"role": "user", "content": "hi"}]
    assert cp.messages_over_budget(small, msg_threshold=28, char_threshold=60_000) is False
    many = [{"role": "user", "content": f"u{i}"} for i in range(30)]
    assert cp.messages_over_budget(many, msg_threshold=28, char_threshold=60_000) is True


def test_should_llm_compact(session_dir: Path) -> None:
    assert cp.should_llm_compact("default") is False
    _write_transcript(session_dir, 8)
    assert cp.should_llm_compact("default") is True
    cp.save_compact_summary("default", "已有摘要")
    # 8 turns, verbatim 3 → older 5; DIGEST_TURNS=12 → not > 12
    assert cp.should_llm_compact("default") is False
    assert cp.should_llm_compact("default", force=True) is True
