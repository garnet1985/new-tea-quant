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
GUIDER_MAX_STEPS = 6

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

# --- 会话 / context 打包 ---
DEFAULT_SESSION_ID = "default"
SESSION_RECENT_TURNS = 6  # 兼容旧调用；打包改用 VERBATIM + DIGEST
SESSION_VERBATIM_TURNS = 3
SESSION_DIGEST_TURNS = 12
SESSION_DIGEST_USER_CHARS = 80
SESSION_DIGEST_REPLY_CHARS = 120
WORKING_KEEP_TOOL_PAIRS = 3
TOOL_RESULT_MSG_MAX_CHARS = 8000
COMPACT_MSG_THRESHOLD = 28
COMPACT_CHAR_THRESHOLD = 60_000
COMPACT_SUMMARY_MAX_CHARS = 4_000
COMPACT_MAX_TOKENS = 800
SESSION_ARCHIVE_AFTER = 200
SESSION_KEEP_ACTIVE = 50

# --- 通用工具 ---
WEB_SEARCH_PROVIDER_ID = "deepseek"
WEB_SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
WEB_SEARCH_TIMEOUT_SECONDS = 30.0
WEB_SEARCH_COUNT_DEFAULT = 5
WEB_SEARCH_COUNT_MAX = 10
READ_FILE_MAX_CHARS = 40_000
READ_URL_MAX_CHARS = 24_000
SEARCH_FILES_MAX_HITS = 40
SEARCH_FILES_MAX_LINE_CHARS = 200
TRADING_CALENDAR_RANGE_MAX_DAYS = 400
PYTHON_SNIPPET_MAX_CHARS = 4_000
PYTHON_SNIPPET_TIMEOUT_SECONDS = 2.0
PYTHON_SNIPPET_RESULT_MAX_CHARS = 8_000
PYTHON_SNIPPET_STDOUT_MAX_CHARS = 4_000

# --- 写盘 / 说明书摘录 ---
WRITE_PATH_LIMIT = 240
WRITE_STRATEGY_MAX_CHARS = 200_000
WRITE_STRATEGY_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "strategy_py", "settings_py", "attribution_py"}
)
WRITE_STRATEGY_ROLLING_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "rolling_py"}
)
WRITE_TAG_MAX_CHARS = 200_000
WRITE_TAG_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "tag_py", "settings_py"}
)
WRITE_TABLE_MAX_CHARS = 200_000
WRITE_TABLE_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "schema_py", "model_py"}
)
WRITE_DATA_SOURCE_MAX_CHARS = 200_000
WRITE_DATA_SOURCE_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "handler_py", "settings_py"}
)
WRITE_DATA_CONTRACT_MAX_CHARS = 200_000
WRITE_DATA_CONTRACT_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "declaration_py", "loader_py", "contract_py"}
)
WRITE_SERIES_RELATION_MAX_CHARS = 200_000
WRITE_SERIES_RELATION_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "settings_py"}
)
WRITE_POST_PROCESS_ADAPTER_MAX_CHARS = 200_000
WRITE_POST_PROCESS_ADAPTER_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"name", "adapter_py", "settings_py"}
)
WRITE_POST_PROCESS_PROCESSOR_MAX_CHARS = 200_000
WRITE_POST_PROCESS_PROCESSOR_ALLOWED_FIELDS: FrozenSet[str] = frozenset(
    {"key", "json_body"}
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

# --- 呈现（ask → work* → present?；content/templates/；与 know_how 分离）---
# scenario → 模版路径；命中规则在 executor/shared/present.py（一 scenario 一模版）
PRESENTATION_SCENARIOS: Dict[str, str] = {
    "backtest_price": "templates/backtest_price.md",
    "backtest_enum": "templates/backtest_enum.md",
    "backtest_portfolio": "templates/backtest_portfolio.md",
}
PRESENT_MAX_TOKENS = 4096
PRESENT_TIMEOUT_SECONDS = 60.0

# --- Userspace 扩展（userspace/extensions/agent/）---
USERSPACE_PROMPT_SNIPPET_MAX_CHARS = 2000
USERSPACE_PROMPT_LANES: FrozenSet[str] = frozenset(
    {"context", "worker", "guider", "present"}
)

# --- 产品设置页（偏好 / 默认 Provider）---
PREFERENCE_MAX_RULES = 40
PREFERENCE_MAX_CHARS = 200
# UI 补充说明写入的 prompt lane（只追加，冲突以产品红线为准）
SETTINGS_CONTEXT_PROMPT_LANE = "context"
