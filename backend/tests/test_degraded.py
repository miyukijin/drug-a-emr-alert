from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import GOOD


def test_missing_model_degrades_gracefully(tmp_path):
    s = Settings(model_path=tmp_path / "nope.joblib")
    with TestClient(create_app(s)) as c:
        assert c.get("/health").json()["status"] == "degraded"
        r = c.post("/api/v1/predict", json=GOOD)
        assert r.status_code == 503 and r.json()["error"]["code"] == "model_unavailable"
