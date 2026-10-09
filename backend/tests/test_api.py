from fastapi.testclient import TestClient

from papertrials.ml.recommender import STARTER_DESIGN

THREE_FLIGHTS = {"flights": [
    {"distance_m": 10.5, "time_s": 1.8, "stability": 3, "wind": 0, "note": "stalled near the end"},
    {"distance_m": 11.0, "time_s": 2.0, "stability": 4, "wind": 0, "note": "stalled again"},
    {"distance_m": 9.5, "wind": 1},
]}


def _fly(client: TestClient, payload: dict) -> dict:
    exp = client.post("/api/experiments", json=payload).json()
    return client.post(f"/api/experiments/{exp['id']}/flights", json=THREE_FLIGHTS).json()


def test_status_on_an_empty_notebook(client: TestClient) -> None:
    status = client.get("/api/status").json()
    assert status["flights"] == 0
    assert status["model_in_use"] is None
    assert status["gemma_available"] is False


def test_first_experiment_has_no_prediction(client: TestClient) -> None:
    exp = client.post("/api/experiments", json=STARTER_DESIGN).json()
    assert exp["number"] == 1
    assert exp["status"] == "planned"
    assert exp["prediction"] is None


def test_logging_flights_marks_experiment_flown_and_writes_lab_note(client: TestClient) -> None:
    exp = _fly(client, STARTER_DESIGN)
    assert exp["status"] == "flown"
    assert exp["median_m"] == 10.5
    assert exp["flights"][0]["issues"] == ["stall"]
    assert exp["flights"][0]["issues_source"] == "keywords"
    assert "10.5" in exp["lab_note"]


def test_full_loop_freezes_the_prediction_made_before_flying(client: TestClient) -> None:
    first = _fly(client, STARTER_DESIGN)
    rec = client.get("/api/recommendation").json()
    assert rec["mode"] == "sweep"
    top = rec["candidates"][0]

    planned = client.post("/api/experiments", json={
        **top["design"], "parent_id": first["id"], "changed_field": top["changed_field"],
    }).json()
    assert planned["changed_field"] == "wing_span_cm"
    assert planned["changed_from"] == STARTER_DESIGN["wing_span_cm"]
    assert planned["prediction"] is not None
    assert "wing span" in planned["hypothesis"]
    frozen = planned["prediction"]

    flown = client.post(f"/api/experiments/{planned['id']}/flights", json=THREE_FLIGHTS).json()
    assert flown["prediction"] == frozen
    assert flown["inside_prediction"] in (True, False)
    assert client.get("/api/insights").json()["baseline"]["experiments"] == 1


def test_out_of_range_design_is_rejected(client: TestClient) -> None:
    response = client.post("/api/experiments", json={**STARTER_DESIGN, "wing_span_cm": 300})
    assert response.status_code == 422


def test_impossible_flight_is_rejected(client: TestClient) -> None:
    exp = client.post("/api/experiments", json=STARTER_DESIGN).json()
    response = client.post(f"/api/experiments/{exp['id']}/flights", json={"flights": [{"distance_m": -2}]})
    assert response.status_code == 422


def test_changed_field_without_parent_is_rejected(client: TestClient) -> None:
    response = client.post("/api/experiments", json={**STARTER_DESIGN, "changed_field": "wing_span_cm"})
    assert response.status_code == 422


def test_unknown_parent_returns_404(client: TestClient) -> None:
    response = client.post("/api/experiments", json={**STARTER_DESIGN, "parent_id": 99, "changed_field": "wing_span_cm"})
    assert response.status_code == 404


def test_deleting_a_parent_keeps_its_children(client: TestClient) -> None:
    parent = _fly(client, STARTER_DESIGN)
    child = client.post("/api/experiments", json={**STARTER_DESIGN, "wing_span_cm": 19, "parent_id": parent["id"], "changed_field": "wing_span_cm"}).json()
    assert client.delete(f"/api/experiments/{parent['id']}").status_code == 204
    assert client.get(f"/api/experiments/{child['id']}").json()["parent_id"] is None


def test_photo_check_without_ollama_returns_503(client: TestClient) -> None:
    exp = client.post("/api/experiments", json=STARTER_DESIGN).json()
    response = client.post(f"/api/experiments/{exp['id']}/photo", files={"photo": ("p.jpg", b"123", "image/jpeg")})
    assert response.status_code == 503


def test_photo_check_rejects_non_images(client: TestClient) -> None:
    exp = client.post("/api/experiments", json=STARTER_DESIGN).json()
    response = client.post(f"/api/experiments/{exp['id']}/photo", files={"photo": ("p.txt", b"123", "text/plain")})
    assert response.status_code == 415


def test_fields_endpoint_lists_every_field(client: TestClient) -> None:
    names = [f["name"] for f in client.get("/api/fields").json()]
    assert "wing_span_cm" in names and "wind" in names


def test_hypothesis_reads_naturally_for_plural_labels(client: TestClient) -> None:
    first = _fly(client, STARTER_DESIGN)
    planned = client.post("/api/experiments", json={
        **STARTER_DESIGN, "winglet_mm": 5, "parent_id": first["id"], "changed_field": "winglet_mm",
    }).json()
    assert planned["hypothesis"].startswith("Changing winglets from 0 mm to 5 mm should move the median distance from 10.5 m")


def test_wind_cannot_be_the_changed_design_field(client: TestClient) -> None:
    parent = _fly(client, STARTER_DESIGN)
    response = client.post("/api/experiments", json={**STARTER_DESIGN, "parent_id": parent["id"], "changed_field": "wind"})
    assert response.status_code == 422


def test_unknown_api_path_is_a_404_not_the_web_page(client: TestClient) -> None:
    assert client.get("/api/nope").status_code == 404
