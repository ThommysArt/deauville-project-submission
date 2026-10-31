import json

from fastapi.testclient import TestClient

from deauville.api import create_app
from deauville.storage import JsonStorage, MemoryStorage

BODY = {
    "kind": "solo",
    "title": "Nora Solo",
    "artist": "nora-lebrun",
    "venue": "le-kiosque",
    "start": "2027-06-13T11:00",
    "duration_minutes": 45,
}


def test_read_routes(client):
    assert client.get("/api/festival").json()["days"][0] == "2027-06-10"
    assert len(client.get("/api/venues").json()) == 4
    artists = client.get("/api/artists").json()
    assert len(artists) == 12 and artists[0]["slug"] == "elodie-marchal"


def test_programme_filters(client):
    assert len(client.get("/api/programme?venue=le-kiosque").json()) == 7
    response = client.get("/api/programme?venue=nowhere")
    assert response.status_code == 404
    assert response.json() == {"detail": "No venue 'nowhere'."}
    assert client.get("/api/programme?day=June 11").status_code == 422


def test_performance_view(client):
    view = client.get("/api/performances/le-kiosque-2027-06-12-0100").json()
    assert view["festival_day"] == "2027-06-11" and view["end"] == "2027-06-12T02:00"
    assert view["acts"] == ["hugo-lemaire", "maya-choukri"]
    workshop = client.get("/api/performances/la-cabane-2027-06-11-1030").json()
    assert workshop["places_left"] == 9


def test_artist_page(client):
    page = client.get("/api/artists/max-pellerin").json()
    assert len(page["performances"]) == 4
    assert client.get("/api/artists/nobody").status_code == 404


def test_now(client):
    data = client.get("/api/now?at=2027-06-11T21:00").json()
    assert [p["title"] for p in data["now_playing"]] == ["Tall Tales"]
    assert len(data["up_next"]) == 3


def test_create_persists_and_conflicts(client, json_storage):
    assert client.post("/api/performances", json=BODY).status_code == 201
    saved = json.loads(json_storage.path.read_text(encoding="utf-8"))
    assert any(p["title"] == "Nora Solo" for p in saved["performances"])
    busy = client.post("/api/performances", json={**BODY, "start": "2027-06-13T11:30"})
    assert busy.status_code == 409 and "busy" in busy.json()["detail"]


def test_invalid_and_malformed(client):
    assert client.post("/api/performances", json={**BODY, "duration_minutes": 0}).status_code == 422
    assert client.post("/api/performances", json={**BODY, "colour": "red"}).status_code == 422
    assert client.post("/api/performances", json={**BODY, "venue": "nowhere"}).status_code == 404


def test_put_changes_id_and_refusal_changes_nothing(client):
    client.post("/api/performances", json=BODY)
    moved = client.put(
        "/api/performances/le-kiosque-2027-06-13-1100", json={"start": "2027-06-13T12:00"}
    )
    assert moved.status_code == 200 and moved.json()["id"] == "le-kiosque-2027-06-13-1200"
    refused = client.put(
        "/api/performances/le-kiosque-2027-06-13-1200", json={"start": "2027-06-12T01:30"}
    )
    assert refused.status_code == 409
    assert client.get("/api/performances/le-kiosque-2027-06-13-1200").status_code == 200


def test_delete_twice(client):
    client.post("/api/performances", json=BODY)
    assert client.delete("/api/performances/le-kiosque-2027-06-13-1100").status_code == 204
    assert client.delete("/api/performances/le-kiosque-2027-06-13-1100").status_code == 404


def test_register_and_full_workshop(client):
    url = "/api/performances/la-cabane-2027-06-11-1030/participants"
    assert client.post(url, json={"name": "New P."}).status_code == 201
    assert client.post(url, json={"name": "new p."}).status_code == 409
    for i in range(8):
        assert client.post(url, json={"name": f"P{i}"}).status_code == 201
    assert client.post(url, json={"name": "Too Many"}).status_code == 409


def test_add_artist_twice(client):
    assert client.post("/api/artists", json={"name": "Zoé Tanguy"}).status_code == 201
    assert client.post("/api/artists", json={"name": "zoe tanguy"}).status_code == 409


def test_unwritable_file_gives_500_and_changes_nothing(json_storage):
    client = TestClient(create_app(json_storage))
    json_storage.path = json_storage.path.parent / "missing_dir" / "f.json"
    assert client.post("/api/performances", json=BODY).status_code == 500
    assert client.get("/api/performances/le-kiosque-2027-06-13-1100").status_code == 404


def test_file_untouched_by_reads(json_storage):
    before = json_storage.path.read_text(encoding="utf-8")
    client = TestClient(create_app(json_storage))
    client.get("/api/programme")
    assert json_storage.path.read_text(encoding="utf-8") == before


def test_storage_is_replaceable():
    assert JsonStorage and MemoryStorage


def test_programme_kind_filter(client):
    shows = client.get("/api/programme?kind=workshop").json()
    assert len(shows) == 4 and {s["kind"] for s in shows} == {"workshop"}
