import pytest
from fastapi.testclient import TestClient
import os
import sys
from pathlib import Path

# Add project roots
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "cli"))

os.environ["FIRE_AI_USE_MOCK"] = "true"

from api.server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_list_csv_files():
    response = client.get("/api/csv-files")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert isinstance(data["files"], list)

def test_get_budgets():
    response = client.get("/api/budgets")
    assert response.status_code == 200
    data = response.json()
    assert "budgets" in data
    # Mock data should return budgets
    assert len(data["budgets"]) > 0

def test_get_analytics():
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "months" in data
    assert "monthly_data" in data
    assert len(data["months"]) > 0

def test_process_transactions_shadow():
    # Use a real file if available, or skip
    csv_response = client.get("/api/csv-files")
    files = csv_response.json().get("files", [])
    if not files:
        pytest.skip("No CSV files found in cli/csv/ for testing")
    
    test_file = files[0]
    payload = {
        "csv_file": test_file,
        "mode": "shadow",
        "auto_date": True
    }
    response = client.post("/api/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["mode"] == "shadow"
    assert "data" in data

def test_process_transactions_live_mock():
    csv_response = client.get("/api/csv-files")
    files = csv_response.json().get("files", [])
    if not files:
        pytest.skip("No CSV files found in cli/csv/ for testing")
    
    test_file = files[0]
    payload = {
        "csv_file": test_file,
        "mode": "live",
        "override": True,
        "auto_date": True
    }
    response = client.post("/api/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["mode"] == "live"
    assert "Successfully updated" in data["message"]
