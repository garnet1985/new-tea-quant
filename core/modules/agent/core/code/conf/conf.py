"""Agent 可调配置：超时、步数、token、Provider 默认等。调试优先改这里。"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet

# --- Provider ---
PRODUCT_PROVIDER_ID = "ntq"
DEV_OWN_DEFAULT_PROVIDER_ID = "deepseek"
OWN_KEYS_ENV = "NTQ_AGENT_OWN_KEYS"
NAVIGATOR_MODE_ENV = "NTQ_AGENT_NAVIGATOR_MODE"

# --- Pipeline / executor 步数 ---
PIPELINE_MAX_STEPS = 14
GUIDER_MAX_STEPS = 4

# --- 补全 ---
ASK_DEFAULT_MAX_TOKENS = 1024
ASK_TEMPERATURE = 0.2
GUIDER_ARCH_MAX_TOKENS = 1600
WORKER_MAX_TOKENS = 4096
WORKER_TIMEOUT_SECONDS = 120.0
# 自备 deepseek 时关闭 thinking，避免占满 max_tokens
WORKER_OWN_EXTRA_PROVIDER_ID = "deepseek"
WORKER_OWN_EXTRA_BODY: Dict[str, Any] = {"thinking": {"type": "disabled"}}

CLASSIFIER_MAX_TOKENS_HEAVY = 512
CLASSIFIER_MAX_TOKENS_LIGHT = 128
CLASSIFIER_TEMPERATURE = 0.0
CLASSIFIER_HEAVY_PROVIDER_IDS: FrozenSet[str] = frozenset({"deepseek", "ntq"})

# --- 工具等待 ---
TOOL_AWAIT_SECONDS = 45 * 60
TOOL_POLL_INTERVAL_SECONDS = 8

# --- 会话 ---
DEFAULT_SESSION_ID = "default"
SESSION_RECENT_TURNS = 6
SESSION_ARCHIVE_AFTER = 200
SESSION_KEEP_ACTIVE = 50

# --- 写盘 / 说明书摘录 ---
WRITE_PATH_LIMIT = 240
WRITE_STRATEGY_MAX_CHARS = 200_000
WRITE_STRATEGY_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "strategy_py", "settings_py", "attribution_py"}
)
DOCS_EXCERPT_MAX_CHARS = 12_000

# --- 模型输出卫生（占位回复视为无效）---
PLACEHOLDER_REPLIES: FrozenSet[str] = frozenset(
    {
        "给人看的话",
        "你的回答",
        "简明中文回答",
        "<简明中文回答>",
        "...",
        "…",
        "工具名",
    }
)
