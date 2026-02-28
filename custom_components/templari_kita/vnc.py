"""VNC client for controlling the Weintek HMI touchscreen."""

import asyncio
import logging
import socket
import struct
import time
from typing import Optional

from Crypto.Cipher import DES

_LOGGER = logging.getLogger(__name__)

# Button coordinates on the SET MANUAL dialog (800x480 screen)
BUTTONS = {
    "home": (180, 45),
    "left_tank": (85, 280),
    "winter_plus": (265, 205),
    "winter_minus": (265, 340),
    "dhw_plus": (400, 205),
    "dhw_minus": (400, 340),
    "summer_plus": (535, 205),
    "summer_minus": (535, 340),
    "ok": (400, 420),
}


def _vnc_des_key(password: str) -> bytes:
    """Convert password to VNC DES key (bit-reversed per byte)."""
    key = bytearray(8)
    pw = password.encode("ascii")[:8]
    for i in range(len(pw)):
        key[i] = pw[i]
    for i in range(8):
        byte = key[i]
        reversed_byte = 0
        for bit in range(8):
            if byte & (1 << bit):
                reversed_byte |= 1 << (7 - bit)
        key[i] = reversed_byte
    return bytes(key)


class VNCClient:
    """Minimal VNC (RFB 3.8) client for sending mouse clicks to the Weintek HMI."""

    def __init__(self, host: str, port: int, password: str) -> None:
        self.host = host
        self.port = port
        self.password = password
        self._sock: Optional[socket.socket] = None

    def _connect_sync(self) -> None:
        """Blocking connect + VNC auth."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((self.host, self.port))

        # RFB handshake
        sock.recv(12)  # server version
        sock.send(b"RFB 003.008\n")
        sock.recv(256)  # security types
        sock.send(bytes([2]))  # select VNC auth

        challenge = sock.recv(16)
        key = _vnc_des_key(self.password)
        des = DES.new(key, DES.MODE_ECB)
        response = des.encrypt(challenge[:8]) + des.encrypt(challenge[8:16])
        sock.send(response)

        result = sock.recv(4)
        if result != b"\x00\x00\x00\x00":
            sock.close()
            raise ConnectionError("VNC authentication failed")

        sock.send(bytes([1]))  # ClientInit: shared
        sock.recv(4096)  # ServerInit (discard)
        self._sock = sock

    def _click_sync(self, x: int, y: int, delay: float = 0.3) -> None:
        """Send a mouse click at (x, y)."""
        if not self._sock:
            raise RuntimeError("Not connected")
        # PointerEvent: type=5, button_mask, x_pos, y_pos
        self._sock.send(struct.pack(">BBhh", 5, 0, x, y))  # move
        self._sock.send(struct.pack(">BBhh", 5, 1, x, y))  # button down
        self._sock.send(struct.pack(">BBhh", 5, 0, x, y))  # button up
        time.sleep(delay)

    def _drain_sync(self) -> None:
        """Drain buffered framebuffer data from VNC."""
        if not self._sock:
            return
        self._sock.settimeout(0.3)
        try:
            while True:
                data = self._sock.recv(65536)
                if not data:
                    break
        except (socket.timeout, OSError):
            pass
        self._sock.settimeout(10)

    def _close_sync(self) -> None:
        """Close the connection."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _adjust_setpoint_sync(
        self, setpoint: str, clicks: int
    ) -> None:
        """
        Open the SET MANUAL dialog and click +/- to adjust a setpoint.

        Args:
            setpoint: "winter", "dhw", or "summer"
            clicks: Positive for increase, negative for decrease.
        """
        if clicks == 0:
            return

        direction = "plus" if clicks > 0 else "minus"
        button_key = f"{setpoint}_{direction}"
        num_clicks = abs(clicks)

        _LOGGER.debug(
            "VNC adjusting %s: %d clicks %s", setpoint, num_clicks, direction
        )

        self._connect_sync()
        try:
            # Navigate to home
            self._click_sync(*BUTTONS["home"], delay=1.5)
            self._drain_sync()

            # Open SET MANUAL dialog (click left tank)
            self._click_sync(*BUTTONS["left_tank"], delay=1.5)
            self._drain_sync()

            # Click +/- the required number of times
            bx, by = BUTTONS[button_key]
            for _ in range(num_clicks):
                self._click_sync(bx, by, delay=0.35)

            self._drain_sync()
        finally:
            self._close_sync()


async def adjust_setpoint(
    hmi_host: str,
    setpoint: str,
    clicks: int,
) -> None:
    """
    Adjust a heat pump setpoint via VNC (async wrapper).

    Runs the blocking VNC session in an executor thread so the HA
    event loop is not blocked.

    Args:
        hmi_host: IP of the Weintek HMI (e.g. "10.0.42.132").
        setpoint: "winter", "dhw", or "summer".
        clicks: Number of 0.5°C steps. Positive = warmer, negative = cooler.
    """
    from .const import VNC_PORT, VNC_PASSWORD

    client = VNCClient(hmi_host, VNC_PORT, VNC_PASSWORD)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, client._adjust_setpoint_sync, setpoint, clicks)
