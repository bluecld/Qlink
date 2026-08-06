#!/usr/bin/env python3
"""Simple SSDP discovery helper.

Broadcasts an M-SEARCH to 239.255.255.250:1900 and prints any responses
received within a short timeout. Useful for verifying that the bridge's
SSDP advertiser is active.
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from typing import Tuple


def send_msearch(st: str, mx: int, timeout: float) -> list[Tuple[Tuple[str, int], str]]:
    message = "\r\n".join(
        [
            "M-SEARCH * HTTP/1.1",
            "HOST: 239.255.255.250:1900",
            'MAN: "ssdp:discover"',
            f"MX: {mx}",
            f"ST: {st}",
            "",
            "",
        ]
    ).encode("utf-8")

    dest = ("239.255.255.250", 1900)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)
    sock.sendto(message, dest)

    responses: list[Tuple[Tuple[str, int], str]] = []
    deadline = time.time() + timeout
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        sock.settimeout(remaining)
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            break
        responses.append((addr, data.decode("utf-8", "ignore")))

    sock.close()
    return responses


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send SSDP M-SEARCH and print responses"
    )
    parser.add_argument(
        "--st", default="ssdp:all", help="Search target (default: ssdp:all)"
    )
    parser.add_argument("--mx", type=int, default=2, help="MX header (default: 2)")
    parser.add_argument(
        "--timeout", type=float, default=3.0, help="Listen timeout in seconds"
    )
    args = parser.parse_args()

    try:
        responses = send_msearch(args.st, args.mx, args.timeout)
    except OSError as exc:
        print(f"Failed to send SSDP discovery: {exc}", file=sys.stderr)
        return 1

    print(f"Received {len(responses)} SSDP response(s)")
    for idx, (addr, payload) in enumerate(responses, 1):
        print("-" * 60)
        print(f"Response #{idx} from {addr[0]}:{addr[1]}")
        print(payload.strip())

    if not responses:
        print("No devices responded. Ensure the bridge is running and SSDP is enabled.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
