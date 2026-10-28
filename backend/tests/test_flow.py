from conftest import as_role


def decide(client, key, role, action, comment=""):
    r = client.post(f"/api/work-items/{key}/decide", json={"action": action, "comment": comment},
                    headers=as_role(role))
    return r


def test_demo_items_are_seeded(client):
    items = client.get("/api/work-items", headers=as_role("developer")).json()
    assert {"INC-4471", "INC-4480", "O2C-162", "O2C-170", "CRM-088"} <= {i["key"] for i in items}


def test_incident_with_code_fix_full_lifecycle(client):
    r = client.post("/api/work-items/INC-4471/start", headers=as_role("ams"))
    assert r.status_code == 200
    assert r.json()["item"]["key"] == "INC-4471" and r.json()["item"]["status"] == "waiting"
    flow = r.json()["flow"]
    assert flow["gate"]["name"] == "recommendation"
    knowledge = flow["outputs"]["knowledge"]
    assert knowledge["needs_code"] is True
    used = [s["ref"] for s in knowledge["sources"] if s["used"]]
    assert "CONF-1002" in used and "INC-3920" in used and "ZCL_SD_SHIP_COND" in used

    # AMS accepts and hands off; the plan then needs a lead or architect
    flow = decide(client, "INC-4471", "ams", "approve").json()["flow"]
    assert flow["gate"]["name"] == "plan"
    assert flow["outputs"]["impact"]["objects"][0]["transports"][0]["id"] == "S4DK912101"
    assert decide(client, "INC-4471", "ams", "approve").status_code == 403

    flow = decide(client, "INC-4471", "lead", "approve").json()["flow"]
    assert flow["gate"]["name"] == "change"
    obj = flow["outputs"]["build"]["objects"][0]
    assert obj["name"] == "ZCL_SD_SHIP_COND" and obj["added"] > 0 and obj["removed"] > 0
    assert flow["outputs"]["build"]["target"]["profile"]["key"] == "full"

    flow = decide(client, "INC-4471", "developer", "approve").json()["flow"]
    assert flow["gate"]["name"] == "pages"
    assert len(flow["outputs"]["document"]["pages"]) == 2
    assert decide(client, "INC-4471", "developer", "approve").status_code == 403

    flow = decide(client, "INC-4471", "lead", "approve").json()["flow"]
    assert flow["done"] is True
    assert len(flow["outputs"]["publish"]["pages"]) == 2

    # The learning loop: published pages are searchable straight away
    hits = client.get("/api/knowledge/search", params={"q": "IDoc shipping condition KNVV"},
                      headers=as_role("developer")).json()
    assert any(h["source"] == "studio" for h in hits)


def test_incident_without_code(client):
    client.post("/api/work-items/INC-4480/start", headers=as_role("ams"))
    assert decide(client, "INC-4480", "developer", "no_code").status_code == 403
    flow = decide(client, "INC-4480", "ams", "no_code").json()["flow"]
    assert flow["resolution"] == "no_code"
    assert flow["gate"]["name"] == "pages"
    assert "build" not in flow["outputs"]


def test_revise_sends_stage_back_with_feedback(client):
    client.post("/api/work-items/O2C-170/start", headers=as_role("developer"))
    assert decide(client, "O2C-170", "developer", "revise").status_code == 400  # comment required
    flow = decide(client, "O2C-170", "developer", "revise", "Use our SM59 naming standard").json()["flow"]
    assert flow["gate"]["name"] == "recommendation"
    assert flow["history"][-1]["comment"] == "Use our SM59 naming standard"


def test_model_admin_rules(client):
    body = {"name": "Local Llama", "provider": "openai_compatible", "model": "llama", "data_level": "production"}
    assert client.post("/api/models", json=body, headers=as_role("developer")).status_code == 403
    assert client.post("/api/models", json=body, headers=as_role("admin")).status_code == 400  # needs URL
    body["api_base"] = "http://localhost:8001/v1"
    created = client.post("/api/models", json=body, headers=as_role("admin")).json()
    assert created["id"] and created["data_level"] == "production"
    assert client.delete(f"/api/models/{created['id']}", headers=as_role("admin")).json() == {"ok": True}


def test_audit_records_decisions(client):
    log = client.get("/api/audit", headers=as_role("pm")).json()
    assert any(e["action"] == "pages: approve" and e["role"] == "lead" for e in log)
