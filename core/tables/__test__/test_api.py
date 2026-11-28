"""Tables 表定义契约测试（对齐 API.md）。"""
from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

import yaml

_TABLES_ROOT = Path(__file__).resolve().parents[1]
_REQUIRED_SCHEMA_KEYS = frozenset(
    {"name", "fields", "primaryKey", "storage_domain", "update_key", "kind"}
)


def _iter_schema_paths() -> list[Path]:
    return sorted(_TABLES_ROOT.rglob("schema.py"))


def _load_schema_dict(schema_path: Path) -> dict:
    spec = importlib.util.spec_from_file_location(
        f"ntq_tables_schema_{schema_path.parent.name}", schema_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = getattr(module, "schema", None)
    assert isinstance(schema, dict), f"{schema_path} 缺少顶层 schema dict"
    return schema


def _model_has_db_subclass(model_path: Path) -> bool:
    tree = ast.parse(model_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "DbBaseModel":
                    return True
                if isinstance(base, ast.Attribute) and base.attr == "DbBaseModel":
                    return True
    return False


def test_every_schema_has_model_pair():
    for schema_path in _iter_schema_paths():
        model_path = schema_path.parent / "model.py"
        assert model_path.is_file(), f"缺少 model.py: {schema_path.parent}"


def test_schema_required_keys_and_sys_prefix():
    for schema_path in _iter_schema_paths():
        schema = _load_schema_dict(schema_path)
        missing = _REQUIRED_SCHEMA_KEYS - set(schema.keys())
        assert not missing, f"{schema_path}: 缺少键 {sorted(missing)}"
        name = str(schema["name"])
        assert name.startswith("sys_"), f"{schema_path}: name 须 sys_ 前缀，得 {name!r}"
        assert isinstance(schema["fields"], list) and schema["fields"], schema_path


def test_each_model_defines_db_base_subclass():
    for schema_path in _iter_schema_paths():
        model_path = schema_path.parent / "model.py"
        assert _model_has_db_subclass(model_path), f"{model_path} 无 DbBaseModel 子类"


def test_glossary_version_matches_module_info():
    info = yaml.safe_load((_TABLES_ROOT / "module_info.yaml").read_text(encoding="utf-8"))
    glossary_head = (_TABLES_ROOT / "glossary.yaml").read_text(encoding="utf-8").splitlines()[:5]
    version_line = next((ln for ln in glossary_head if ln.startswith("# Version:")), "")
    match = re.search(r"# Version:\s*(\S+)", version_line)
    assert match, "glossary.yaml 缺少 # Version:"
    assert match.group(1) == info["version"]