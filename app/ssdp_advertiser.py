#!/usr/bin/env python3
"""
SSDP Advertiser for Vantage QLink Bridge
Broadcasts SSDP advertisements so SmartThings can discover the bridge via LAN.
"""

import socket
import struct
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger("qlink.ssdp")

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 3
SSDP_ST = "urn:schemas-upnp-org:device:Basic:1"

# SmartThings-specific discovery
ST_SSDP_ALL = "ssdp:all"
ST_ROOT_DEVICE = "upnp:rootdevice"


class SSDPAdvertiser:
    """Advertises the bridge via SSDP for SmartThings LAN discovery."""

    def __init__(
        self,
        local_ip: str,
        local_port: int = 8000,
        uuid: str = "vantage-qlink-bridge-001",
        interval: int = 30,
    ):
        """
        Args:
            local_ip: Local IP address of the bridge
            local_port: Port the bridge REST API is running on
            uuid: Unique identifier for this bridge instance
            interval: Broadcast interval in seconds (default 30)
        """
        self.local_ip = local_ip
        self.local_port = local_port
        self.uuid = uuid
        self.interval = interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sock: Optional[socket.socket] = None

    def _build_notify_message(self, notification_type: str) -> bytes:
        """Build SSDP NOTIFY message."""
        location = f"http://{self.local_ip}:{self.local_port}/about"
        usn = f"uuid:{self.uuid}::{notification_type}"

        message = (
            "NOTIFY * HTTP/1.1\r\n"
            f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
            "CACHE-CONTROL: max-age=1800\r\n"
            f"LOCATION: {location}\r\n"
            f"NT: {notification_type}\r\n"
            f"NTS: ssdp:alive\r\n"
            f"SERVER: Vantage QLink Bridge/1.0\r\n"
            f"USN: {usn}\r\n"
            "\r\n"
        )
        return message.encode("utf-8")

    def _build_response_message(self, search_target: str) -> bytes:
        """Build SSDP M-SEARCH response message."""
        location = f"http://{self.local_ip}:{self.local_port}/about"
        usn = f"uuid:{self.uuid}"
        if search_target != ST_ROOT_DEVICE and search_target != ST_SSDP_ALL:
            usn = f"{usn}::{search_target}"

        message = (
            "HTTP/1.1 200 OK\r\n"
            "CACHE-CONTROL: max-age=1800\r\n"
            "EXT:\r\n"
            f"LOCATION: {location}\r\n"
            "SERVER: Vantage QLink Bridge/1.0\r\n"
            f"ST: {search_target}\r\n"
            f"USN: {usn}\r\n"
            "\r\n"
        )
        return message.encode("utf-8")

    def _send_notification(self):
        """Send SSDP NOTIFY messages for all supported types."""
        if not self.sock:
            return

        notification_types = [
            ST_ROOT_DEVICE,
            f"uuid:{self.uuid}",
            SSDP_ST,
        ]

        for nt in notification_types:
            message = self._build_notify_message(nt)
            try:
                self.sock.sendto(message, (SSDP_ADDR, SSDP_PORT))
                logger.debug(f"Sent SSDP NOTIFY for {nt}")
            except Exception as e:
                logger.error(f"Failed to send NOTIFY for {nt}: {e}")

    def _listen_for_search(self):
        """Listen for SSDP M-SEARCH requests and respond."""
        # Create separate socket for receiving M-SEARCH requests
        listen_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # Bind to SSDP multicast address
            listen_sock.bind(("", SSDP_PORT))

            # Join multicast group
            mreq = struct.pack("4sl", socket.inet_aton(SSDP_ADDR), socket.INADDR_ANY)
            listen_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            listen_sock.settimeout(1.0)

            logger.info(
                f"Listening for SSDP M-SEARCH requests on {SSDP_ADDR}:{SSDP_PORT}"
            )

            while self.running:
                try:
                    data, addr = listen_sock.recvfrom(1024)
                    message = data.decode("utf-8", errors="ignore")

                    # Check if it's an M-SEARCH request
                    if "M-SEARCH" in message and "ST:" in message:
                        # Extract search target
                        search_target = None
                        for line in message.split("\r\n"):
                            if line.startswith("ST:"):
                                search_target = line.split(":", 1)[1].strip()
                                break

                        if search_target and self._should_respond(search_target):
                            logger.info(
                                f"Received M-SEARCH from {addr[0]} for {search_target}"
                            )
                            # Wait a bit to avoid flooding
                            time.sleep(0.5)
                            response = self._build_response_message(search_target)
                            listen_sock.sendto(response, addr)
                            logger.info(f"Sent M-SEARCH response to {addr[0]}")

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error in M-SEARCH listener: {e}")

        finally:
            listen_sock.close()

    def _should_respond(self, search_target: str) -> bool:
        """Check if we should respond to this search target."""
        return search_target in [
            ST_SSDP_ALL,
            ST_ROOT_DEVICE,
            SSDP_ST,
            f"uuid:{self.uuid}",
        ]

    def _advertise_loop(self):
        """Main advertising loop."""
        logger.info(f"Starting SSDP advertiser for {self.local_ip}:{self.local_port}")
        logger.info(f"UUID: {self.uuid}, Interval: {self.interval}s")

        # Create socket for sending NOTIFY
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        # Start M-SEARCH listener in separate thread
        search_thread = threading.Thread(target=self._listen_for_search, daemon=True)
        search_thread.start()

        try:
            # Send initial notification
            self._send_notification()

            # Continue sending periodic notifications
            while self.running:
                time.sleep(self.interval)
                if self.running:
                    self._send_notification()

        except Exception as e:
            logger.error(f"SSDP advertiser error: {e}")
        finally:
            if self.sock:
                # Send byebye notification
                self._send_byebye()
                self.sock.close()
                self.sock = None
            logger.info("SSDP advertiser stopped")

    def _send_byebye(self):
        """Send SSDP byebye notification on shutdown."""
        if not self.sock:
            return

        notification_types = [
            ST_ROOT_DEVICE,
            f"uuid:{self.uuid}",
            SSDP_ST,
        ]

        for nt in notification_types:
            usn = f"uuid:{self.uuid}::{nt}"

            message = (
                "NOTIFY * HTTP/1.1\r\n"
                f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
                f"NT: {nt}\r\n"
                f"NTS: ssdp:byebye\r\n"
                f"USN: {usn}\r\n"
                "\r\n"
            ).encode("utf-8")

            try:
                self.sock.sendto(message, (SSDP_ADDR, SSDP_PORT))
                logger.debug(f"Sent SSDP byebye for {nt}")
            except Exception as e:
                logger.error(f"Failed to send byebye for {nt}: {e}")

    def start(self):
        """Start the SSDP advertiser in background thread."""
        if self.running:
            logger.warning("SSDP advertiser already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._advertise_loop, daemon=True)
        self.thread.start()
        logger.info("SSDP advertiser started")

    def stop(self):
        """Stop the SSDP advertiser."""
        if not self.running:
            return

        logger.info("Stopping SSDP advertiser...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None


def get_local_ip() -> Optional[str]:
    """Get the local IP address of this machine."""
    try:
        # Connect to a public DNS server (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return None


if __name__ == "__main__":
    # Test the SSDP advertiser
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    local_ip = get_local_ip()
    if not local_ip:
        logger.error("Could not determine local IP address")
        exit(1)

    advertiser = SSDPAdvertiser(local_ip=local_ip, local_port=8000)
    advertiser.start()

    try:
        logger.info("Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        advertiser.stop()
