"""
`DataEntity`：句柄侧「已定稿、数据匣仍空」的类型（目标语义见 `CONCEPTS.md` §2）。

由 `DataContractManager.issue_handle` 构造；物化走 `load`；流程说明见同包 `pipeline.py`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.modules.data_contract.runtime.resolver_registry import ResolverRegistry


@dataclass
class DataEntity:
    """
    - **data_id**：与 `DataKey` / 注册表一致的字符串 id。
    - **params**：合并后的运行参数（scenario、窗口、覆盖项等；合并规则见 `merge_params`）。
    - **meta**：规则类快照（scope、时间轴字段等），由 `build_rule_meta` 生成。
    - **loaded**：`load()` 成功后可由调用方写入；框架不强制缓存策略。
    """

    data_id: str
    params: Mapping[str, Any] = field(default_factory=dict)
    meta: Mapping[str, Any] = field(default_factory=dict)
    loaded: Any = None

    def load(self, registry: ResolverRegistry, **kwargs: Any) -> Any:
        """
        用 `data_id` 解析 **resolver**，执行 `resolver(self, **kwargs)` 完成物化。

        kwargs 通常由外层编排注入（如 `entity_id`、DataManager、连接信息等），**不在**句柄 issue 时写死。
        """
        if not isinstance(registry, ResolverRegistry):
            raise TypeError(f"load() expects ResolverRegistry, got {type(registry)!r}")
        fn = registry.resolve(self.data_id)
        out = fn(self, **kwargs)
        self.loaded = out
        return out

    def clear_loaded(self) -> None:
        """释放句柄上缓存的物化结果引用（不调用 resolver）。"""
        self.loaded = None
