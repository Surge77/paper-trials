import pytest
from fastapi.testclient import TestClient

from papertrials import demo
from papertrials.ml.recommender import STARTER_DESIGN

SAMPLE = [
    {"id": 1, "number": 1, "created_at": "2026-10-06T10:00:00+00:00", "status": "flown", "parent_id": None,
     **STARTER_DESIGN, "flights": [{"id": 1, "created_at": "2026-10-06T10:05:00+00:00", "distance_m": 9.0, "issues": []}]},
    {"id": 2, "number": 2, "created_at": "2026-10-06T10:10:00+00:00", "status": "flown", "parent_id": 1,
     **STARTER_DESIGN, "wing_span_cm": 19, "changed_field": "wing_span_cm",
     "flights": [{"id": 2, "created_at": "2026-10-06T10:15:00+00:00", "distance_m": 10.0, "issues": []}]},
]


@pytest.fixture(autouse=True)
def sample_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(demo, "demo_records", lambda: [{**r, "flights": [dict(f) for f in r["flights"]]} for r in SAMPLE])


def test_sample_data_loads_flagged_as_demo(client: TestClient) -> None:
    assert client.post("/api/demo").json() == {"loaded": 2}
    experiments = client.get("/api/experiments").json()
    assert all(e["is_demo"] for e in experiments)
    assert experiments[1]["parent_id"] == experiments[0]["id"]
    assert client.get("/api/status").json()["has_demo_data"] is True


def test_sample_data_only_loads_into_an_empty_notebook(client: TestClient) -> None:
    client.post("/api/experiments", json=STARTER_DESIGN)
    assert client.post("/api/demo").status_code == 409


def test_clearing_sample_data_keeps_your_own_experiments(client: TestClient) -> None:
    client.post("/api/demo")
    sample_parent = client.get("/api/experiments").json()[1]["id"]
    mine = client.post("/api/experiments", json={**STARTER_DESIGN, "wing_span_cm": 20, "parent_id": sample_parent, "changed_field": "wing_span_cm"}).json()

    assert client.delete("/api/demo").json() == {"removed": 2}
    remaining = client.get("/api/experiments").json()
    assert [e["id"] for e in remaining] == [mine["id"]]
    assert remaining[0]["parent_id"] is None
