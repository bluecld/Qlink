import json
from fastapi.testclient import TestClient

from app.bridge import app, qlink_send


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


def test_config_endpoint():
    r = client.get("/config")
    assert r.status_code == 200
    data = r.json()
    assert "ip" in data
    assert "port" in data
    assert "fade" in data
    assert "rooms" in data
