#!/usr/bin/env python3
"""Test harness for the QLink bridge.

Usage examples (PowerShell):
  # start mock server (in one terminal)
  python .\scripts\mock_vantage.py --host 127.0.0.1 --port 2323

  # set env so the bridge points to the mock (if running the bridge locally)
  $env:VANTAGE_IP = '127.0.0.1'; $env:VANTAGE_PORT = '2323'

  # call harness (in another terminal)
  python .\scripts\test_harness.py --bridge http://127.0.0.1:8000 --device 251 --level 50

This script sends POSTs to /device/{id}/set and GET /send/{cmd} and prints responses.
"""

import argparse
import requests
import json


def post_set(bridge_url, device, level=None, switch=None):
    url = f"{bridge_url.rstrip('/')}/device/{device}/set"
    payload = {}
    if switch is not None:
        payload["switch"] = switch
    if level is not None:
        payload["level"] = int(level)
    r = requests.post(url, json=payload, timeout=5)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


def get_send(bridge_url, cmd):
    url = f"{bridge_url.rstrip('/')}/send/{cmd}"
    r = requests.get(url, timeout=5)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--bridge", default="http://127.0.0.1:8000", help="Bridge base URL")
    p.add_argument("--device", type=int, default=251)
    p.add_argument("--level", type=int, help="Level 0-100 to set")
    p.add_argument("--switch", choices=["on", "off"], help="switch on/off")
    p.add_argument("--raw", help="send raw command via /send/{cmd}")
    args = p.parse_args()

    if args.raw:
        code, resp = get_send(args.bridge, args.raw)
        print("GET /send result:", code)
        print(json.dumps(resp, indent=2) if isinstance(resp, (dict, list)) else resp)
    else:
        code, resp = post_set(
            args.bridge, args.device, level=args.level, switch=args.switch
        )
        print("POST /device/{id}/set result:", code)
        print(json.dumps(resp, indent=2) if isinstance(resp, (dict, list)) else resp)
