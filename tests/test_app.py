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

    # /api/leds/{station} serves from the poll cache by default; force=true
    # exercises the live-query path, which also warms the cache.
    r = client.get("/api/leds/23?force=true")
    assert r.status_code == 200
    data = r.json()
    assert data["station"] == 23
    assert data["station_id"] == "V23"
    assert data["cached"] is False
    # On bits: buttons 3,4,7 -> 255; blink bit -> button 6 -> 128
    assert data["leds"][2] == 255
    assert data["leds"][3] == 255
    assert data["leds"][5] == 128
    assert data["button_states"]["3"] == "on"
    assert data["button_states"]["6"] == "blink"


def test_get_station_leds_detailed(monkeypatch):
    monkeypatch.setattr("app.bridge.get_station_master", lambda station: 1)
    monkeypatch.setattr("app.bridge.qlink_send", lambda cmd: "RLT 1 23 4C 20")

    # RLT detailed response parses the same on/blink hex (4C/20).
    r = client.get("/api/leds/23?force=true")
    assert r.status_code == 200
    data = r.json()
    assert data["leds"][2] == 255
    assert data["leds"][5] == 128
    assert data["button_states"]["3"] == "on"
    assert data["button_states"]["6"] == "blink"


def test_get_station_leds_served_from_cache(monkeypatch):
    """Without force, the endpoint must NOT hit the enabler (no live query)."""
    import app.bridge as b

    # Warm the cache directly, as the background poll would.
    b.update_station_leds(31, {3: "on", 6: "blink"})

    def _boom(cmd):
        raise AssertionError("qlink_send must not be called without force=true")

    monkeypatch.setattr("app.bridge.qlink_send", _boom)
    r = client.get("/api/leds/31")
    assert r.status_code == 200
    data = r.json()
    assert data["cached"] is True
    assert data["leds"][2] == 255
    assert data["leds"][5] == 128


def test_get_all_loads_aggregated(monkeypatch):
    # Setup a fake loads.json list
    monkeypatch.setattr(
        "app.bridge._get_load_list",
        lambda: [{"id": 101}, {"id": 102}, {"id": 103}],
    )

    # Stub qlink_send to return final integer level
    def fake_q(cmd):
        # expect 'VGL@ <id>' - return a numeric string
        parts = cmd.split()
        return "75" if parts[-1] == "101" else "0"

    monkeypatch.setattr("app.bridge.qlink_send", fake_q)

    r = client.get("/api/loads")
    assert r.status_code == 200
    data = r.json()
    assert "loads" in data
    assert data["count"] == 3
    assert data["loads"]["101"] == 75


def test_get_all_loads_fallback(monkeypatch):
    # Simulate older runtime where _update_loads_cache doesn't exist
    # Remove the attribute if present
    monkeypatch.delattr("app.bridge", "_update_loads_cache", raising=False)

    monkeypatch.setattr(
        "app.bridge._get_load_list",
        lambda: [{"id": 201}, {"id": 202}],
    )

    def fake_q2(cmd):
        return "33" if cmd.endswith("201") else "66"

    monkeypatch.setattr("app.bridge.qlink_send", fake_q2)

    r = client.get("/api/loads?force=true")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert data["loads"]["201"] == 33
