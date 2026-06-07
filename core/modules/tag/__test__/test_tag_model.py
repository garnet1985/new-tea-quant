"""TagModel 单元测试。"""
from __future__ import annotations

import pytest

from core.modules.tag.models.tag_model import TagModel


class TestTagModel:
    def test_create_from_settings(self):
        tag = TagModel.create_from_settings(
            {
                "name": "test_tag",
                "display_name": "Test Tag Display",
                "description": "Test description",
            }
        )
        assert tag.get_name() == "test_tag"
        assert tag.tag_name == "test_tag"
        assert tag.display_name == "Test Tag Display"
        assert tag.description == "Test description"

        default = TagModel.create_from_settings({"name": "test_tag"})
        assert default.display_name == "test_tag"
        assert default.description == ""

    @pytest.mark.parametrize(
        "tag_setting,expected",
        [
            ({"name": "test_tag"}, True),
            ({}, False),
            ({"name": ""}, False),
            ({"name": None}, False),
        ],
    )
    def test_is_setting_valid(self, tag_setting, expected):
        assert TagModel.is_setting_valid(tag_setting) is expected

    def test_from_dict_and_to_dict_roundtrip(self):
        tag = TagModel.from_dict(
            {
                "id": 1,
                "tag_name": "test_tag",
                "scenario_id": 10,
                "display_name": "Test Tag Display",
                "description": "Test description",
                "created_at": "2024-01-01",
                "updated_at": "2024-01-02",
            }
        )
        assert tag.id == 1
        assert tag.tag_name == "test_tag"
        assert tag.scenario_id == 10

        out = tag.to_dict()
        assert out["id"] == 1
        assert out["tag_name"] == "test_tag"
        assert out["scenario_id"] == 10
        assert out["display_name"] == "Test Tag Display"
        assert out["description"] == "Test description"
        assert out["created_at"] == "2024-01-01"
        assert out["updated_at"] == "2024-01-02"

    def test_get_settings(self):
        tag = TagModel.create_from_settings(
            {
                "name": "test_tag",
                "display_name": "Test Tag Display",
                "description": "Test description",
            }
        )
        settings = tag.get_settings()
        assert settings["name"] == "test_tag"
        assert settings["display_name"] == "Test Tag Display"
        assert settings["description"] == "Test description"

    @pytest.mark.parametrize(
        "tag_setting,db_meta,expected",
        [
            (
                {"name": "test_tag", "display_name": "New Display Name"},
                {"display_name": "Old Display Name", "description": ""},
                True,
            ),
            (
                {"name": "test_tag", "description": "New description"},
                {"display_name": "test_tag", "description": "Old description"},
                True,
            ),
            (
                {
                    "name": "test_tag",
                    "display_name": "Test Tag",
                    "description": "Test description",
                },
                {"display_name": "Test Tag", "description": "Test description"},
                False,
            ),
        ],
    )
    def test_has_meta_diff(self, tag_setting, db_meta, expected):
        tag = TagModel.create_from_settings(tag_setting)
        assert tag._has_meta_diff(db_meta) is expected
