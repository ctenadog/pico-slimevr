"""VRChat OSC helpers.

SlimeVR can push FBT to VRChat over OSC instead of (or in addition to) the
SteamVR driver. VRChat itself has no config file for this — OSC is toggled in
game — but the port pairing is easy to get wrong, so we generate a reference
profile and can test the ports locally.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from pathlib import Path

# SlimeVR sends tracker data to VRChat's input port and listens on the output one.
OSC_DEFAULTS = {
    "host": "127.0.0.1",
    "send_port": 9000,
    "receive_port": 9001,
}

DEFAULT_TRACKERS = ["Waist", "LeftFoot", "RightFoot"]


@dataclass
class PortCheck:
    port: int
    free: bool
    detail: str


def build_profile(
    *,
    host: str = OSC_DEFAULTS["host"],
    send_port: int = OSC_DEFAULTS["send_port"],
    receive_port: int = OSC_DEFAULTS["receive_port"],
    trackers: list[str] | None = None,
) -> dict:
    return {
        "host": host,
        "send_port": send_port,
        "receive_port": receive_port,
        "trackers": trackers if trackers is not None else list(DEFAULT_TRACKERS),
        "note": (
            "Вставьте эти значения в SlimeVR: Settings -> OSC -> VRChat OSC Trackers. "
            "В VRChat включите OSC в радиальном меню (Options -> OSC)."
        ),
    }


def write_profile(path: Path, **kwargs) -> Path:
    profile = build_profile(**kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(profile, handle, indent=2, ensure_ascii=False)
    return path


def check_port(port: int, *, host: str = "127.0.0.1") -> PortCheck:
    """A free UDP port means nothing else is listening there yet."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port))
    except OSError as error:
        return PortCheck(port, False, f"порт занят: {error}")
    finally:
        sock.close()
    return PortCheck(port, True, "порт свободен")


def check_ports(**kwargs) -> list[PortCheck]:
    host = kwargs.get("host", OSC_DEFAULTS["host"])
    return [
        check_port(OSC_DEFAULTS["send_port"], host=host),
        check_port(OSC_DEFAULTS["receive_port"], host=host),
    ]


def firewall_commands(ports: tuple[int, int] | None = None) -> list[str]:
    """netsh rules the user can run as administrator to allow OSC through."""
    send, receive = ports or (OSC_DEFAULTS["send_port"], OSC_DEFAULTS["receive_port"])
    rules = []
    for name, port in (("VRChat OSC In", send), ("VRChat OSC Out", receive)):
        rules.append(
            f'netsh advfirewall firewall add rule name="{name}" '
            f"dir=in action=allow protocol=UDP localport={port}"
        )
    return rules
