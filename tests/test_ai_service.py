"""Unit tests for ai-service/main.py."""
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

# Load ai-service/main.py under a unique module name to avoid a collision with
# backend/main.py (both files are named main.py).
AI_MAIN = Path(__file__).resolve().parent.parent / "ai-service" / "main.py"
spec = importlib.util.spec_from_file_location("ai_service_main", AI_MAIN)
ai_service_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_service_main)

client = TestClient(ai_service_main.app)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["model"] == "nba-stats-predictor-v1"


def test_predict_trends():
    resp = client.post("/api/ai/predict", json={"team": "Celtics"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_used"] == "nba-stats-predictor-v1"
    assert "prediction" in body


def test_metrics_endpoint():
    client.get("/health")
    client.post("/api/ai/predict", json={"team": "Celtics"})
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "http_requests_total" in body or "http_request_duration" in body
    assert 'handler="/health"' not in body
