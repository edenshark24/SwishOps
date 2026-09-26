"""Unit tests for backend/main.py."""
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

# Load backend/main.py under a unique module name to avoid a collision with
# ai-service/main.py (both files are named main.py).
BACKEND_MAIN = Path(__file__).resolve().parent.parent / "backend" / "main.py"
spec = importlib.util.spec_from_file_location("backend_main", BACKEND_MAIN)
backend_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_main)

client = TestClient(backend_main.app)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert "environment" in body


def test_get_nba_stats():
    resp = client.get("/api/nba/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "matchups" in body
    assert body["matchups"][0]["home"] == "Boston Celtics"
