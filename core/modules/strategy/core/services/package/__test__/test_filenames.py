"""Tests for package download filename helpers."""

from __future__ import annotations

import pytest

from core.modules.strategy.core.services.package.filenames import (
    bundle_filename,
    parse_export_target,
    single_entity_filename,
)


def test_bundle_filename_sanitizes_path():
    assert bundle_filename("demo/random/x") == "demo_random_x-strategy.zip"


def test_single_entity_filename():
    assert single_entity_filename("tag", "a/b") == "a_b-tag.zip"
    with pytest.raises(ValueError):
        single_entity_filename("nope", "x")


def test_parse_export_target():
    assert parse_export_target("demo") == ("bundle", "demo")
    assert parse_export_target("tag:foo") == ("tag", "foo")
    with pytest.raises(ValueError):
        parse_export_target("weird:foo")
