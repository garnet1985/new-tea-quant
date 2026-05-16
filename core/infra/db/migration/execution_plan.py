"""
将 :class:`~core.infra.db.migration.schema_diff.SchemaDiffResult` 编译为可顺序执行的 DDL 步骤。

当前自动策略（保守）：

- **新建表**：``CREATE TABLE IF NOT EXISTS`` + 各 ``CREATE INDEX IF NOT EXISTS``。
- **仅新增列**：先按旧 schema **丢弃该表全部二级索引**，再 ``ADD COLUMN``（新列一律按可空写入，避免已有行违反 NOT NULL），再按**新** schema **重建索引**。
- **仅索引变化**（无字段增删改）：对变更索引 ``DROP`` + ``CREATE``。
- **删表 / 删列 / 改列类型等**：不生成 DDL，抛出 :class:`MigrationPlanError`，需走 ``core/infra/update/db`` 脚本。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.infra.db.schema_management.field import Field
from core.infra.db.schema_management.schema_manager import SchemaManager
from core.infra.db.migration.schema_diff import SchemaDiffResult, TableSchemaDiff


class MigrationPlanError(ValueError):
    """无法自动生成安全迁移计划（例如删列、改列）。"""


class MigrationStepKind(str, Enum):
    CREATE_TABLE = "create_table"
    DROP_SECONDARY_INDEX = "drop_secondary_index"
    ADD_COLUMN = "add_column"
    CREATE_INDEX = "create_index"
    RUN_DATA_SCRIPT = "run_data_script"


@dataclass
class MigrationStep:
    """单条迁移步骤（DDL 或数据脚本）。"""

    step_id: str
    kind: MigrationStepKind
    action_id: str
    sql: str = ""
    depends_on: Tuple[str, ...] = ()
    script_action_id: Optional[str] = None


@dataclass
class ExecutionPlan:
    """内存中的迁移计划；可选由调用方自行落盘 JSON。"""

    steps: List[MigrationStep] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _quote(sm: SchemaManager, name: str) -> str:
    return sm.quote_ddl_identifier(name)


def _drop_index_sql(database_type: str, sm: SchemaManager, table_name: str, index_name: str) -> str:
    qt = _quote(sm, table_name)
    qi = _quote(sm, index_name)
    if database_type == "mysql":
        return f"ALTER TABLE {qt} DROP INDEX {qi}"
    return f"DROP INDEX IF EXISTS {qi}"


def _add_column_sql(sm: SchemaManager, table_name: str, field_dict: Dict[str, Any]) -> str:
    fd = dict(field_dict)
    fd["nullable"] = True
    fd["isNullable"] = True
    field_obj = Field.from_dict(fd)
    col = _quote(sm, field_obj.name)
    qt = _quote(sm, table_name)
    frag = f"{col} {field_obj.to_sql(sm.database_type)}"
    frag += field_obj.get_not_null_sql()
    frag += field_obj.get_default_sql(sm.database_type)
    return f"ALTER TABLE {qt} ADD COLUMN {frag}"


def _action_id_for_table(new_schema: Optional[Dict[str, Any]], table_name: str) -> str:
    if new_schema and isinstance(new_schema.get("update_key"), str) and new_schema["update_key"].strip():
        return new_schema["update_key"].strip()
    return table_name


def plan_from_schema_diff(
    diff: SchemaDiffResult,
    schema_manager: SchemaManager,
    *,
    old_schemas: Dict[str, Dict[str, Any]],
    new_schemas: Dict[str, Dict[str, Any]],
) -> ExecutionPlan:
    """
    根据 diff 与旧/新完整 schema 字典生成 :class:`ExecutionPlan`。

    Args:
        diff: :func:`~core.infra.db.migration.schema_diff.diff_expected_schemas` 的结果
        schema_manager: 用于方言引用与 ``CREATE TABLE`` / ``CREATE INDEX`` SQL 生成（``database_type`` 须已设置）
        old_schemas: 与 diff 左侧一致的快照
        new_schemas: 与 diff 右侧一致的新期望
    """
    steps: List[MigrationStep] = []
    warnings: List[str] = []
    db_type = schema_manager.database_type

    def push(step: MigrationStep) -> None:
        steps.append(step)

    for td in diff.tables:
        if td.kind == "unchanged":
            continue
        if td.kind == "removed":
            warnings.append(
                f"表 {td.table_name!r} 在新版期望 schema 中已删除；未自动生成 DROP TABLE，需人工或脚本处理。"
            )
            continue
        if td.kind == "added":
            ns = new_schemas.get(td.table_name)
            if not ns:
                raise MigrationPlanError(f"内部错误：新增表 {td.table_name!r} 不在 new_schemas 中")
            aid = _action_id_for_table(ns, td.table_name)
            create_sql = schema_manager.generate_create_table_sql(ns)
            push(
                MigrationStep(
                    step_id=f"create_table:{td.table_name}",
                    kind=MigrationStepKind.CREATE_TABLE,
                    action_id=aid,
                    sql=create_sql,
                )
            )
            for idx in ns.get("indexes") or []:
                if not isinstance(idx, dict) or not idx.get("name"):
                    continue
                ix_sql = schema_manager.generate_create_index_sql(td.table_name, idx)
                push(
                    MigrationStep(
                        step_id=f"create_index:{td.table_name}:{idx['name']}",
                        kind=MigrationStepKind.CREATE_INDEX,
                        action_id=aid,
                        sql=ix_sql,
                        depends_on=(f"create_table:{td.table_name}",),
                    )
                )
            continue

        if td.kind != "modified":
            continue

        ns = new_schemas.get(td.table_name)
        os_ = old_schemas.get(td.table_name)
        if not ns:
            raise MigrationPlanError(f"表 {td.table_name!r} 标记为 modified 但 new_schemas 中缺失")
        aid = _action_id_for_table(ns, td.table_name)

        if not td.field_changes and not td.index_changes:
            warnings.append(
                f"表 {td.table_name!r} 在 diff 中标记为 modified 但无字段/索引定义变化（可能仅 update_key 等），未生成 DDL。"
            )
            continue

        for fc in td.field_changes:
            if fc.kind == "remove":
                raise MigrationPlanError(
                    f"表 {td.table_name!r} 删除字段 {fc.field_name!r} 不支持自动生成计划，请使用数据迁移脚本。"
                )
            if fc.kind == "alter":
                raise MigrationPlanError(
                    f"表 {td.table_name!r} 变更字段 {fc.field_name!r} 定义不支持自动生成计划，请使用数据迁移脚本。"
                )

        field_adds = [fc for fc in td.field_changes if fc.kind == "add"]
        strip_all_secondaries = td.has_field_ddl_change()

        if strip_all_secondaries and os_:
            for idx in os_.get("indexes") or []:
                if not isinstance(idx, dict) or not idx.get("name"):
                    continue
                iname = str(idx["name"])
                push(
                    MigrationStep(
                        step_id=f"drop_index:{td.table_name}:{iname}",
                        kind=MigrationStepKind.DROP_SECONDARY_INDEX,
                        action_id=aid,
                        sql=_drop_index_sql(db_type, schema_manager, td.table_name, iname),
                    )
                )

        dep_strip: Tuple[str, ...] = tuple(
            f"drop_index:{td.table_name}:{str(idx.get('name'))}"
            for idx in (os_.get("indexes") or [])
            if isinstance(idx, dict) and idx.get("name")
        ) if (strip_all_secondaries and os_) else ()

        prev_dep: Optional[str] = None
        for fc in field_adds:
            assert fc.new is not None
            sid = f"add_column:{td.table_name}:{fc.field_name}"
            sql = _add_column_sql(schema_manager, td.table_name, fc.new)
            deps: Tuple[str, ...] = dep_strip
            if prev_dep:
                deps = deps + (prev_dep,)
            push(
                MigrationStep(
                    step_id=sid,
                    kind=MigrationStepKind.ADD_COLUMN,
                    action_id=aid,
                    sql=sql,
                    depends_on=deps,
                )
            )
            prev_dep = sid

        if strip_all_secondaries:
            last_col_dep = prev_dep
            for idx in ns.get("indexes") or []:
                if not isinstance(idx, dict) or not idx.get("name"):
                    continue
                iname = str(idx["name"])
                ix_sql = schema_manager.generate_create_index_sql(td.table_name, idx)
                deps2: Tuple[str, ...] = dep_strip
                if last_col_dep:
                    deps2 = deps2 + (last_col_dep,)
                push(
                    MigrationStep(
                        step_id=f"create_index:{td.table_name}:{iname}",
                        kind=MigrationStepKind.CREATE_INDEX,
                        action_id=aid,
                        sql=ix_sql,
                        depends_on=deps2,
                    )
                )
            continue

        # 仅索引变化
        for ic in td.index_changes:
            if ic.kind in ("remove", "alter") and ic.old and ic.old.get("name"):
                iname = str(ic.old["name"])
                push(
                    MigrationStep(
                        step_id=f"drop_index:{td.table_name}:{iname}",
                        kind=MigrationStepKind.DROP_SECONDARY_INDEX,
                        action_id=aid,
                        sql=_drop_index_sql(db_type, schema_manager, td.table_name, iname),
                    )
                )
        for ic in td.index_changes:
            if ic.kind in ("add", "alter") and ic.new and ic.new.get("name"):
                iname = str(ic.new["name"])
                ix_sql = schema_manager.generate_create_index_sql(td.table_name, ic.new)
                drop_id = f"drop_index:{td.table_name}:{iname}" if ic.kind == "alter" else None
                deps3: Tuple[str, ...] = (drop_id,) if drop_id else ()
                push(
                    MigrationStep(
                        step_id=f"create_index:{td.table_name}:{iname}",
                        kind=MigrationStepKind.CREATE_INDEX,
                        action_id=aid,
                        sql=ix_sql,
                        depends_on=deps3,
                    )
                )

    return ExecutionPlan(steps=steps, warnings=warnings)


def topological_sort_steps(steps: List[MigrationStep]) -> List[MigrationStep]:
    """按 ``depends_on`` 拓扑排序；未知依赖 ID 忽略（仍保持稳定顺序）。"""
    by_id = {s.step_id: s for s in steps}
    seen: set[str] = set()
    out: List[MigrationStep] = []

    def visit(sid: str) -> None:
        if sid in seen:
            return
        st = by_id.get(sid)
        if st is None:
            return
        for d in st.depends_on:
            if d and d in by_id:
                visit(d)
        seen.add(sid)
        out.append(st)

    for s in steps:
        visit(s.step_id)
    return out


def ordered_plan(plan: ExecutionPlan) -> List[MigrationStep]:
    """返回依依赖关系展开后的步骤列表（用于执行）。"""
    return topological_sort_steps(plan.steps)
