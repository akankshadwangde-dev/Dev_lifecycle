"""Runs after test_flow: ends by switching the sample data off."""

from conftest import as_role


def test_manual_item(client):
    r = client.post("/api/work-items", json={"kind": "change", "title": "Extend ZSD_R_BLOCKED_ORDERS"},
                    headers=as_role("functional"))
    assert r.status_code == 200
    item = r.json()["item"]
    assert item["key"].startswith("REQ-") and item["source"] == "manual"
    assert item["objects"] == ["ZSD_R_BLOCKED_ORDERS"]
    assert client.post("/api/work-items", json={"title": "x"}, headers=as_role("pm")).status_code == 403
    dup = client.post("/api/work-items", json={"title": "y", "key": item["key"]}, headers=as_role("developer"))
    assert dup.status_code == 409


def test_project_settings_need_admin(client):
    body = {"name": "Test project", "sap_release": 750, "sap_cloud": False, "sample_data": True}
    assert client.put("/api/project", json=body, headers=as_role("lead")).status_code == 403
    project = client.put("/api/project", json=body, headers=as_role("admin")).json()
    assert project["sap_release"] == 750 and project["setup"]["model"] is True


def test_switching_sample_data_off_removes_it(client):
    body = {"name": "Test project", "sap_release": None, "sap_cloud": False, "sample_data": False}
    project = client.put("/api/project", json=body, headers=as_role("admin")).json()
    assert project["sample_data"] is False and project["setup"]["model"] is False

    keys = {i["key"] for i in client.get("/api/work-items", headers=as_role("developer")).json()}
    assert keys and all(k.startswith("REQ-") for k in keys)  # only the manually added item is left
    assert client.get("/api/knowledge/sources", headers=as_role("developer")).json() == {}
    log = client.get("/api/audit", headers=as_role("admin")).json()
    assert not any(e["item_key"] == "INC-4471" for e in log)

    # Without sample data and without a model, analysis explains what is missing
    key = next(iter(keys))
    flow = client.post(f"/api/work-items/{key}/start", headers=as_role("developer")).json()["flow"]
    assert "Add or enable one under Settings > AI models" in flow["error"]
