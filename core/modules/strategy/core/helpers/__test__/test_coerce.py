"""ValueCoerce：空串 / Enum → 标量。"""
from __future__ import annotations

from enum import Enum

import pytest

from core.modules.strategy.core.helpers.coerce import ValueCoerce

pytestmark = pytest.mark.force_run


class _Kind(str, Enum):
    COMPLETE = "complete"


def test_as_str_reads_enum_value() -> None:
    assert ValueCoerce.as_str(_Kind.COMPLETE) == "complete"
    assert ValueCoerce.as_str(None) == ""
    assert ValueCoerce.as_str("  a  ") == "a"


def test_optional_and_tuple() -> None:
    assert ValueCoerce.as_float("") == 0.0
    assert ValueCoerce.as_optional_float("") is None
    assert ValueCoerce.as_optional_bool("1") is True
    assert ValueCoerce.as_optional_bool("") is None
    assert ValueCoerce.as_str_tuple(["st", " ", "star_st"]) == ("st", "star_st")
