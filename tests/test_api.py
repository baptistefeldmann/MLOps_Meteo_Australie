import sys
from unittest.mock import MagicMock, patch

# conftest.py already mocked dagshub/mlflow/xgboost, but src.models.predict
# also executes get_model() at module level — mock the whole module before import.
sys.modules["src.models.predict"] = MagicMock(
    predict_RainTomorrow=MagicMock(return_value={"prediction": "No", "probability": 0.3}),
    TARGET="RainTomorrow",
)
sys.modules["src.data.collect_inference"] = MagicMock(
    collect_inference_data=MagicMock(return_value="data/inference/Sydney_2024.json"),
)

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_returns_success():
    response = client.post("/predict", json={"city": "Sydney"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["city"] == "Sydney"


def test_predict_missing_city_returns_422():
    response = client.post("/predict", json={})
    assert response.status_code == 422
