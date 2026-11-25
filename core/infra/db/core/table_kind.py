"""表种类：schema.kind 与表名第二段。

物理表名固定为 ``{owner}_{kind}_{subject}``。
owner 为 ``sys``（core/tables）或 ``cust``（userspace/extensions/tables）。
kind 与 ``storage_domain`` 无关，存储域不写进表名。
"""
from __future__ import annotations

import re
from typing import FrozenSet, Optional

TABLE_OWNERS: FrozenSet[str] = frozenset({"sys", "cust"})
TABLE_KINDS: FrozenSet[str] = frozenset({"data", "map", "cache", "tmp", "meta"})

_NAME_RE = re.compile(
    r"^(sys|cust)_(data|map|cache|tmp|meta)_([a-z][a-z0-9_]*)$"
)


def validate_table_identity(schema: dict, *, owner: Optional[str] = None) -> str:
    """校验必填 ``kind``，并要求表名第二段与之相同。返回归一化后的 kind。"""
    table_name = str(schema.get("name") or "")
    raw = schema.get("kind")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            f"表 {table_name!r} 缺少 kind，允许值: {', '.join(sorted(TABLE_KINDS))}"
        )
    kind = raw.strip().lower()
    if kind not in TABLE_KINDS:
        raise ValueError(
            f"表 {table_name!r} 的 kind={raw!r} 无效，"
            f"允许值: {', '.join(sorted(TABLE_KINDS))}"
        )
    schema["kind"] = kind

    match = _NAME_RE.match(table_name)
    if match is None:
        raise ValueError(
            f"表名 {table_name!r} 须为 {{sys|cust}}_{{kind}}_主题，"
            f"kind 取 {', '.join(sorted(TABLE_KINDS))}"
        )
    owner_in_name, kind_in_name, _subject = match.groups()
    if kind_in_name != kind:
        raise ValueError(
            f"表 {table_name!r} 的 kind={kind!r} 与表名中的种类 {kind_in_name!r} 不一致"
        )
    if owner is not None and owner_in_name != owner:
        raise ValueError(
            f"表 {table_name!r} 的属主须为 {owner!r}，当前是 {owner_in_name!r}"
        )
    return kind
