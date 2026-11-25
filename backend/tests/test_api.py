from tests.conftest import GOOD


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["model_loaded"] and r["patients_loaded"] == 4020


def test_predict_returns_probability(client):
    r = client.post("/api/v1/predict", json=GOOD)
    assert r.status_code == 200
    b = r.json()
    assert 0 <= b["likelihood_treated"] <= 1
    assert abs(b["likelihood_treated"] + b["likelihood_untreated"] - 1) < 1e-3
    assert b["eligible"] is True and b["drivers"]


def test_predict_normalises_case_and_flags_unseen_category(client):
    r = client.post("/api/v1/predict", json={**GOOD, "physician_type": "astro-physician", "patient_gender": "f"})
    assert r.status_code == 200
    assert any("astro-physician".upper() in u for u in r.json()["unseen_categories"])


def test_low_likelihood_eligible_patient_alerts(client):
    r = client.post("/api/v1/predict", json={**GOOD, "patient_age": 35, "num_conditions": 1,
                                             "physician_type": "UNKNOWN", "physician_state": "UNKNOWN",
                                             "location_type": "INDEPENDENT LABORATORY"}).json()
    assert r["eligible"] and r["alert"] and r["tier"] == "LOW"


def test_child_never_alerts(client):
    r = client.post("/api/v1/predict", json={**GOOD, "patient_age": 8, "location_type": "INDEPENDENT LABORATORY"}).json()
    assert not r["eligible"] and not r["alert"]


def test_validation_error_envelope(client):
    r = client.post("/api/v1/predict", json={**GOOD, "patient_age": 400, "patient_gender": "X"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error" and err["request_id"]
    assert {d["field"] for d in err["details"]} >= {"patient_age", "patient_gender"}


def test_malformed_json(client):
    r = client.post("/api/v1/predict", content="{bad", headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_batch(client):
    r = client.post("/api/v1/predict/batch", json={"patients": [GOOD, {**GOOD, "patient_age": 20}]})
    assert r.status_code == 200 and r.json()["count"] == 2


def test_batch_empty_rejected(client):
    assert client.post("/api/v1/predict/batch", json={"patients": []}).status_code == 422


def test_patient_lookup_and_404(client):
    ok = client.get("/api/v1/patients/5")
    assert ok.status_code == 200 and ok.json()["patient_id"] == 5
    nf = client.get("/api/v1/patients/9999999")
    assert nf.status_code == 404 and nf.json()["error"]["code"] == "not_found"


def test_worklist_filters_and_sorting(client):
    r = client.get("/api/v1/patients", params={"alerts_only": True, "page_size": 50}).json()
    assert r["total"] > 0 and all(i["alert"] and i["eligible"] for i in r["items"])
    probs = [i["likelihood_treated"] for i in r["items"]]
    assert probs == sorted(probs)
    assert client.get("/api/v1/patients", params={"page_size": 500}).status_code == 422


def test_model_info(client):
    b = client.get("/api/v1/model").json()
    assert b["alert_threshold"] == 0.15 and b["holdout_metrics"]


def test_request_id_echoed(client):
    r = client.get("/health", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
