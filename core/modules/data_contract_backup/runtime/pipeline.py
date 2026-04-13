"""
## 主链路（目标形态，与 `CONCEPTS.md` 对齐）

编排通常按下面顺序；**谁调用 `load`** 由 Strategy / Tag / Worker 外层决定，框架不在句柄 issue 时隐式拉数。

1. **句柄 issue** — `DataContractManager.issue_handle(key, params=..., context=...)`
   - 用 `ContractRouteRegistry` 解析 `key` + `context`（如 tag_kind）→ 得到 **规则类实例**；
   - `build_rule_meta(contract)` → 写入 `DataEntity.meta`；`params` 写入 `DataEntity.params`；
   - 此时 **数据匣仍空**。

2. **load 物化** — `DataEntity.load(resolver_registry, **kwargs)`
   - 用 `data_id` 在 `ResolverRegistry` 中查找 **resolver**；
   - `resolver(data_entity, **kwargs)` 返回裸数据或业务视图（由注册实现；内部可调 DataManager）。

3. **校验 raw（数据封闭）** — `DataContractManager.validate_raw(key, raw, context=...)`
   - 解析规则类 → 调用规则类上的 **`validate_raw(raw)`**；
   - 失败 fail-closed，成功得到可下游消费的数据。

**与「句柄 issue」区分**：只有 **`issue_handle` → `DataEntity`** 表示句柄定稿；**`validate_raw`** 表示对已取得的 raw 做规则校验。
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional


def merge_params(
    defaults: Mapping[str, Any],
    overrides: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    合并参数：**defaults** 为底，**overrides** 显式覆盖（浅合并）。

    深合并/字段级规则在实现里集中扩展；当前为 MVP。
    """
    out: dict[str, Any] = dict(defaults)
    if overrides:
        out.update(dict(overrides))
    return out


def apply_param_overrides(
    target: MutableMapping[str, Any],
    overrides: Optional[Mapping[str, Any]] = None,
) -> None:
    """就地写入 overrides（若有）。"""
    if not overrides:
        return
    target.update(dict(overrides))
