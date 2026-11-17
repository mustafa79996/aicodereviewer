from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_get_samples():
    res = client.get("/api/samples")
    assert res.status_code == 200
    data = res.json()
    assert "python" in data
    assert "javascript" in data

def test_post_review_endpoint():
    payload = {
        "code": "def hello():\n    if 1 == None: pass\n    return 'world'",
        "language": "python",
        "filename": "hello.py",
        "ai_provider": "built-in",
        "run_ai_deep_review": False
    }
    res = client.post("/api/review", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "quality_score" in data
    assert "issues" in data
    assert "corrected_code" in data
    assert "unified_diff" in data

def test_history_and_analytics():
    # History list
    hist_res = client.get("/api/history")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)

    # Analytics
    analytics_res = client.get("/api/analytics")
    assert analytics_res.status_code == 200
    data = analytics_res.json()
    assert "totals" in data
