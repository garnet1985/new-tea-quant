"""
比较两份「期望 schema」（通常为升级前快照 vs 当前 ``core/tables``），产出结构化 diff。

不包含数据库 introspection；与真实库对齐在后续阶段扩展。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


TableChangeKind = Literal["added", "removed", "modified", "unchanged"]
FieldChangeKind = Literal["add", "remove", "alter"]
IndexChangeKind = Literal["add", "remove", "alter"]


def _index_sig(idx: Dict[str, Any]) -> Tuple[str, Tuple[str, ...], bool]:
    name = str(idx.get("name", ""))
    fields = idx.get("fields") or []
    if not isinstance(fields, list):
        fields = []
    return (name, tuple(str(f) for f in fields), bool(idx.get("unique", False)))


def _index_map(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for idx in schema.get("indexes") or []:
        if isinstance(idx, dict) and idx.get("name"):
            out[str(idx["name"])] = idx
    return out


def _field_cmp_tuple(d: Dict[str, Any]) -> Tuple[Any, ...]:
    """用于判断字段 DDL 是否变化（忽略纯说明类字段）。"""
    return (
        str(d.get("type", "")).lower(),
        d.get("length"),
        d.get("precision"),
        d.get("scale"),
        bool(d.get("isRequired", False)),
        bool(d.get("nullable", d.get("isNullable", True))),
        bool(d.get("autoIncrement", False) or d.get("isAutoIncrement", False)),
        repr(d.get("default")),
    )


def _fields_by_name(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    fields = schema.get("fields") or []
    if not isinstance(fields, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for fd in fields:
        if isinstance(fd, dict) and fd.get("name"):
            out[str(fd["name"])] = fd
    return out


@dataclass
class FieldChange:
    kind: FieldChangeKind
    field_name: str
    old: Optional[Dict[str, Any]] = None
    new: Optional[Dict[str, Any]] = None


@dataclass
class IndexChange:
    kind: IndexChangeKind
    index_name: str
    old: Optional[Dict[str, Any]] = None
    new: Optional[Dict[str, Any]] = None


@dataclass
class TableSchemaDiff:
    """单表在旧、新期望 schema 之间的差异。"""

    table_name: str
    kind: TableChangeKind
    update_key_old: Optional[str] = None
    update_key_new: Optional[str] = None
    field_changes: List[FieldChange] = field(default_factory=list)
    index_changes: List[IndexChange] = field(default_factory=list)

    def has_field_ddl_change(self) -> bool:
        return any(c.kind in ("add", "remove", "alter") for c in self.field_changes)

    def has_index_change(self) -> bool:
        return any(c.kind in ("add", "remove", "alter") for c in self.index_changes)


@dataclass
class SchemaDiffResult:
    """``diff_expected_schemas`` 的返回值。"""

    tables: List[TableSchemaDiff] = field(default_factory=list)

    def non_unchanged(self) -> List[TableSchemaDiff]:
        return [t for t in self.tables if t.kind != "unchanged"]


def diff_expected_schemas(
    old_schemas: Dict[str, Dict[str, Any]],
    new_schemas: Dict[str, Dict[str, Any]],
) -> SchemaDiffResult:
    """
    对比两份 ``{表名: schema dict}``（表名即 ``schema[\"name\"]`` 的 key）。

    Args:
        old_schemas: 升级前期望（例如快照 JSON 反序列化结果）
        new_schemas: 升级后期望（例如当前 ``SchemaManager.load_all_schemas()``）

    Returns:
        结构化 diff；未变化的表也会列出 ``kind=\"unchanged\"`` 便于调试（可通过
        :meth:`SchemaDiffResult.non_unchanged` 过滤）。
    """
    old_names = set(old_schemas.keys())
    new_names = set(new_schemas.keys())
    all_names = sorted(old_names | new_names)
    out: List[TableSchemaDiff] = []

    for name in all_names:
        o = old_schemas.get(name)
        n = new_schemas.get(name)

        if o is None and n is not None:
            out.append(
                TableSchemaDiff(
                    table_name=name,
                    kind="added",
                    update_key_new=(str(n.get("update_key")) if n.get("update_key") else None),
                )
            )
            continue
        if n is None and o is not None:
            out.append(
                TableSchemaDiff(
                    table_name=name,
                    kind="removed",
                    update_key_old=(str(o.get("update_key")) if o.get("update_key") else None),
                )
            )
            continue
        assert o is not None and n is not None

        uk_o = str(o.get("update_key")) if o.get("update_key") else None
        uk_n = str(n.get("update_key")) if n.get("update_key") else None

        fo, fn = _fields_by_name(o), _fields_by_name(n)
        field_names = sorted(set(fo.keys()) | set(fn.keys()))
        f_changes: List[FieldChange] = []
        for fnm in field_names:
            co, cn = fo.get(fnm), fn.get(fnm)
            if co is None and cn is not None:
                f_changes.append(FieldChange("add", fnm, None, cn))
            elif cn is None and co is not None:
                f_changes.append(FieldChange("remove", fnm, co, None))
            elif co is not None and cn is not None:
                if _field_cmp_tuple(co) != _field_cmp_tuple(cn):
                    f_changes.append(FieldChange("alter", fnm, co, cn))

        im_o, im_n = _index_map(o), _index_map(n)
        idx_names = sorted(set(im_o.keys()) | set(im_n.keys()))
        i_changes: List[IndexChange] = []
        for inm in idx_names:
            io, ine = im_o.get(inm), im_n.get(inm)
            if io is None and ine is not None:
                i_changes.append(IndexChange("add", inm, None, ine))
            elif ine is None and io is not None:
                i_changes.append(IndexChange("remove", inm, io, None))
            elif io is not None and ine is not None:
                if _index_sig(io) != _index_sig(ine):
                    i_changes.append(IndexChange("alter", inm, io, ine))

        if not f_changes and not i_changes and uk_o == uk_n:
            out.append(
                TableSchemaDiff(
                    table_name=name,
                    kind="unchanged",
                    update_key_old=uk_o,
                    update_key_new=uk_n,
                )
            )
        else:
            out.append(
                TableSchemaDiff(
                    table_name=name,
                    kind="modified",
                    update_key_old=uk_o,
                    update_key_new=uk_n,
                    field_changes=f_changes,
                    index_changes=i_changes,
                )
            )

    return SchemaDiffResult(tables=out)
