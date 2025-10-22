from app import bridge


def test_decode_led_hex_basic():
    # Example from docstring: on=4C, blink=20
    states = bridge.decode_led_hex("4C", "20")
    assert isinstance(states, dict)
    assert len(states) == 8
    # Button 3,4,7 are on (4C => 01001100), button 6 is blink (20 => 00100000)
    assert states[3] == "on"
    assert states[4] == "on"
    assert states[7] == "on"
    assert states[6] == "blink"


def test_decode_led_hex_invalid():
    # Non-hex input should return empty dict per implementation
    states = bridge.decode_led_hex("ZZ", "GG")
    assert states == {}


def test_parse_vantage_event_sw():
    msg = "SW 1 23 5 1 0001"
    evt = bridge.parse_vantage_event(msg)
    assert evt is not None
    assert evt["type"] == "button"
    assert evt["master"] == 1
    assert evt["station"] == 23
    assert evt["button"] == 5
    assert evt["state"] == "pressed"


def test_parse_vantage_event_le():
    msg = "LE 1 19 4C 20"
    evt = bridge.parse_vantage_event(msg)
    assert evt is not None
    assert evt["type"] == "led_keypad"
    assert evt["station"] == 19
    assert "button_states" in evt
    assert isinstance(evt["button_states"], dict)


def test_parse_vantage_event_ls_lo_lv_lc():
    # LS
    evt = bridge.parse_vantage_event("LS 1 23 2 128")
    assert evt and evt["type"] == "load_station"
    assert evt["level"] == 128

    # LO
    evt = bridge.parse_vantage_event("LO 1 2 3 4 200")
    assert evt and evt["type"] == "load_module"
    assert evt["level"] == 200

    # LV
    evt = bridge.parse_vantage_event("LV 1 12 90")
    assert evt and evt["type"] == "load_variable"
    assert evt["variable"] == 12

    # LC
    evt = bridge.parse_vantage_event("LC 1 23 4 1")
    assert evt and evt["type"] == "led_lcd"
    assert evt["state"] == "on"


def test_parse_vantage_event_unknown():
    msg = "FOO 1 2 3"
    evt = bridge.parse_vantage_event(msg)
    # Unknown events return an event with type 'unknown' but not None
    assert evt is not None
    assert evt.get("type") == "unknown"


def test_qlink_send_retries(monkeypatch):
    # Simulate connection refused for the first 2 attempts then success
    calls = {"count": 0}

    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass

        def sendall(self, data):
            pass

        def settimeout(self, t):
            pass

        def recv(self, n):
            return b"OK"

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    def fake_create_connection(addr, timeout=None):
        # Raise OSError on first two calls to simulate refused connection
        calls["count"] += 1
        if calls["count"] < 3:
            raise OSError("Connection refused")
        return FakeSocket()

    monkeypatch.setattr("socket.create_connection", fake_create_connection)

    # Force low retry values for speed
    orig_max = bridge.QLINK_MAX_RETRIES
    orig_base = bridge.QLINK_RETRY_BASE_SEC
    bridge.QLINK_MAX_RETRIES = 4
    bridge.QLINK_RETRY_BASE_SEC = 0.001

    try:
        resp = bridge.qlink_send("TEST 1")
        assert resp == "OK"
        assert calls["count"] >= 3
    finally:
        bridge.QLINK_MAX_RETRIES = orig_max
        bridge.QLINK_RETRY_BASE_SEC = orig_base
