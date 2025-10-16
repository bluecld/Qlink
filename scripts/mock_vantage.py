#!/usr/bin/env python3
"""Simple mock Vantage IP-Enabler TCP server for local testing.

Usage: python scripts/mock_vantage.py [--host HOST] [--port PORT]

This server accepts simple ASCII commands and returns canned responses for
testing the bridge. It supports VLO (write) and VGL (read) style commands.
"""
import argparse
import socket
import threading


RESP_OK = "OK"


def handle_client(conn, addr, devices):
    with conn:
        data = b""
        try:
            data = conn.recv(4096)
        except Exception:
            return
        if not data:
            return
        text = data.decode("ascii", errors="ignore").strip()
        # Strip CR/CRLF
        text = text.rstrip("\r\n")
        parts = text.split()
        if not parts:
            conn.sendall(b"\r")
            return
        cmd = parts[0].upper()
        if cmd == "VLO" and len(parts) >= 3:
            # VLO <id> <level> [fade]
            try:
                dev = int(parts[1])
                lvl = int(parts[2])
                devices[dev] = lvl
                resp = f"VLO {dev} {lvl}"
            except Exception:
                resp = "ERR"
            conn.sendall((resp + "\r").encode("ascii"))
            return
        if cmd == "VGL" and len(parts) >= 2:
            try:
                dev = int(parts[1])
                lvl = devices.get(dev, 0)
                resp = f"VGL {dev} {lvl}"
            except Exception:
                resp = "ERR"
            conn.sendall((resp + "\r").encode("ascii"))
            return
        # default echo
        conn.sendall((RESP_OK + "\r").encode("ascii"))


def run_server(host: str, port: int):
    devices = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    print(f"Mock Vantage listening on {host}:{port}")
    try:
        while True:
            conn, addr = sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr, devices))
            t.daemon = True
            t.start()
    finally:
        sock.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=2323)
    args = p.parse_args()
    run_server(args.host, args.port)
