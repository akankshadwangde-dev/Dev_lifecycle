import pytest

from app.connectors.sap_profiles import detect, syntax_level
from app.llm.gateway import Gateway, NoModelAvailable, candidates
from app.models import ModelConfig
from app.roles import may_decide
from app.textutil import find_objects, parse_json


@pytest.mark.parametrize("release, cloud, profile, syntax", [
    (758, False, "full", "v758"),
    (750, False, "full", "v750"),
    (740, False, "full", "v740"),
    (731, False, "hybrid", "v702"),
    (702, False, "hybrid", "v702"),
    (700, False, "basic", "v700"),
    (None, False, "basic", "v700"),
    (None, True, "cloud", "cloud"),
])
def test_release_profiles(release, cloud, profile, syntax):
    assert detect(release, cloud).key == profile
    assert syntax_level(release, cloud) == syntax


def _model(id, level, stages=(), provider="demo", priority=100, enabled=True):
    return ModelConfig(id=id, project_id=1, name=f"m{id}", provider=provider, model="x",
                       data_level=level, stages=list(stages), priority=priority, enabled=enabled)


def test_gateway_respects_data_levels_and_order():
    models = [_model(1, "public"), _model(2, "code", priority=50), _model(3, "production", ["build"]),
              _model(4, "production", enabled=False)]
    assert [m.id for m in candidates(models, "build", "code")] == [3, 2]
    assert [m.id for m in candidates(models, "plan", "code", preferred_id=3)] == [3, 2]
    assert [m.id for m in candidates(models, "plan", "production")] == [3]
    # The user's choice cannot widen what a model may see
    assert [m.id for m in candidates(models, "plan", "code", preferred_id=1)] == [2, 3]


def test_gateway_falls_back_and_reports():
    gw = Gateway([_model(1, "code", provider="nope", priority=1), _model(2, "code", priority=2)])
    assert gw.complete("plan", "s", "ITEM_KEY: X\nTITLE: T").model_name == "m2"
    with pytest.raises(NoModelAvailable):
        Gateway([_model(1, "public")]).complete("plan", "s", "p", data_level="code")


def test_gate_permissions():
    assert may_decide("ams", "recommendation", "no_code")
    assert not may_decide("developer", "recommendation", "no_code")
    assert not may_decide("ams", "plan", "approve")
    assert may_decide("architect", "plan", "approve")
    assert may_decide("developer", "change", "approve")
    assert not may_decide("developer", "pages", "approve")
    assert may_decide("developer", "pages", "revise")
    assert not may_decide("pm", "plan", "revise")


def test_text_helpers():
    assert find_objects("fix ZCL_SD_SHIP_COND=>APPLY_DEFAULT and zsd_r_test") == [
        "ZCL_SD_SHIP_COND=>APPLY_DEFAULT", "ZSD_R_TEST"]
    assert parse_json('Sure:\n```json\n{"a": 1}\n```') == {"a": 1}
