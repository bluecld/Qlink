from fastapi.testclient import TestClient

from app.bridge import app


client = TestClient(app)


def test_about():
    r = client.get("/about")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data and data["name"] == "qlink-bridge"


def test_send_raw(monkeypatch):
    # Stub qlink_send to avoid network
    monkeypatch.setattr("app.bridge.qlink_send", lambda cmd: "OK")
    r = client.get("/send/TESTCMD")
    assert r.status_code == 200
    data = r.json()
    assert data["command"] == "TESTCMD"
    assert data["response"] == "OK"


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_set_device_invalid_switch():
    r = client.post("/device/1/set", json={"switch": "maybe"})
    assert r.status_code == 400
    data = r.json()
    assert data["ok"] is False
    assert data["error"]
    assert "on/off" in data["detail"].lower()


def test_config_endpoint():
    r = client.get("/config")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "qlink-bridge"
    assert "version" in data
    assert "timeout" in data


def test_manifest_endpoint():
    r = client.get("/manifest")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "qlink-bridge"
    assert "endpoints" in data and isinstance(data["endpoints"], list)


def test_get_station_leds_regular(monkeypatch):
    monkeypatch.setattr("app.bridge.get_station_master", lambda station: 1)
    monkeypatch.setattr("app.bridge.qlink_send", lambda cmd: "4C 20")

    r = client.get("/api/leds/23")
    assert r.status_code == 200
    data = r.json()
    assert data["station"] == 23
    assert data["station_id"] == "V23"
    # On bits: buttons 3,4,7 -> 255; blink bit -> button 6 -> 128
    assert data["leds"][2] == 255
    assert data["leds"][3] == 255
    assert data["leds"][5] == 128
    assert data["button_states"]["3"] == "on"
    assert data["button_states"]["6"] == "blink"


def test_get_station_leds_detailed(monkeypatch):
    monkeypatch.setattr("app.bridge.get_station_master", lambda station: 1)
    monkeypatch.setattr("app.bridge.qlink_send", lambda cmd: "RLT 1 23 4C 20")

    r = client.get("/api/leds/23")
    assert r.status_code == 200
    data = r.json()
    assert data["on_leds"] == "4C"
    assert data["blink_leds"] == "20"
