import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client():
    with TestClient(create_app()) as c:
        yield c


GOOD = {"patient_age": 71, "patient_gender": "F", "num_conditions": 2,
        "physician_type": "FAMILY MEDICINE", "physician_state": "CA", "location_type": "TELEHEALTH"}
