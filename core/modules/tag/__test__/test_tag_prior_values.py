from core.modules.tag.components.job_staging.tag_prior_values import (
    load_latest_tag_value_json,
    parse_tag_value_bool,
)


def test_load_latest_from_inject_prior():
    payload = {
        "_inject": {
            "prior_tag_values": {"2": '{"value": true}'},
        }
    }
    raw = load_latest_tag_value_json(
        payload,
        None,
        entity_id="000001.SZ",
        tag_definition_id=2,
    )
    assert raw == '{"value": true}'
    assert parse_tag_value_bool(raw) is True


def test_load_latest_without_inject_returns_none_without_service():
    assert (
        load_latest_tag_value_json({}, None, entity_id="x", tag_definition_id=1) is None
    )
