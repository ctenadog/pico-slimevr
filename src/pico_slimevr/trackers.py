"""SteamVR tracker roles.

SteamVR stores assigned roles in ``steamvr.vrsettings`` under a top-level
``trackers`` object::

    "trackers": {
        "/devices/SlimeVR/human://LEFT_FOOT": "TrackerRole_LeftFoot"
    }

We read and (optionally) write that mapping. Roles are only *suggested*: writing
a device key SteamVR has not seen yet is harmless but also does nothing until
that device appears, so this is best used after the SlimeVR driver is running.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .detect import Environment

# human://<point> -> TrackerRole_<X>, matching SlimeVR's driver device names.
DESIRED_ROLES = {
    "CHEST": "TrackerRole_Chest",
    "WAIST": "TrackerRole_Waist",
    "HIP": "TrackerRole_Waist",
    "LEFT_KNEE": "TrackerRole_LeftKnee",
    "RIGHT_KNEE": "TrackerRole_RightKnee",
    "LEFT_FOOT": "TrackerRole_LeftFoot",
    "RIGHT_FOOT": "TrackerRole_RightFoot",
}

_ROLE_RE = re.compile(r"^TrackerRole_(?P<role>[A-Za-z]+)$")
_POINT_RE = re.compile(r"human://(?P<point>[A-Za-z_]+)", re.IGNORECASE)


@dataclass
class TrackerEntry:
    device: str
    role: str

    @property
    def point(self) -> str | None:
        match = _POINT_RE.search(self.device)
        return match.group("point").upper() if match else None

    @property
    def role_name(self) -> str:
        match = _ROLE_RE.match(self.role)
        return match.group("role") if match else self.role


def read_roles(vrsettings: Path | None) -> dict[str, str]:
    if vrsettings is None or not vrsettings.is_file():
        return {}
    try:
        with vrsettings.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    trackers = data.get("trackers") if isinstance(data, dict) else None
    if not isinstance(trackers, dict):
        return {}
    return {str(k): str(v) for k, v in trackers.items()}


def list_trackers(env: Environment) -> list[TrackerEntry]:
    return [TrackerEntry(device, role) for device, role in read_roles(env.vrsettings_file).items()]


def problems(entries: list[TrackerEntry]) -> list[str]:
    """Human readable notes about roles that look wrong or disabled."""
    notes: list[str] = []
    for entry in entries:
        if entry.role in ("TrackerRole_Handed", "TrackerRole_Disabled", "TrackerRole_Camera"):
            label = entry.point or entry.device
            notes.append(f"{label}: роль {entry.role_name} — трекер фактически отключён")
            continue
        point = entry.point
        if point is None:
            continue
        expected = DESIRED_ROLES.get(point)
        if expected is not None and entry.role != expected:
            notes.append(f"{point}: роль {entry.role_name}, ожидается {role_name(point)}")
    return notes


def role_name(point: str) -> str:
    return DESIRED_ROLES.get(point, "").replace("TrackerRole_", "")


def apply_roles(
    env: Environment,
    *,
    points: list[str] | None = None,
    dry_run: bool = False,
) -> "RoleResult":
    """Force ``TrackerRole_*`` for SlimeVR device keys found in vrsettings."""
    vrsettings = env.vrsettings_file
    if vrsettings is None:
        return RoleResult(False, "steamvr.vrsettings не найден (запустите SteamVR хотя бы раз).")

    wanted = {p.upper() for p in points} if points else set(DESIRED_ROLES)
    entries = read_roles(vrsettings)
    if not entries:
        return RoleResult(
            False,
            "В steamvr.vrsettings нет секции trackers — сначала запустите SteamVR с трекерами.",
        )

    changes: dict[str, str] = {}
    for device, role in entries.items():
        point = TrackerEntry(device, role).point
        if point is None or point not in wanted:
            continue
        desired = DESIRED_ROLES.get(point)
        if desired is not None and role != desired:
            changes[device] = desired

    if not changes:
        return RoleResult(False, "Роли уже выставлены правильно.")

    if dry_run:
        return RoleResult(True, f"Будет обновлено ролей: {len(changes)}")

    with vrsettings.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    backup = vrsettings.with_suffix(vrsettings.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(vrsettings, backup)
    data.setdefault("trackers", {}).update(changes)
    with vrsettings.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=3, ensure_ascii=False)
    return RoleResult(True, f"Обновлено ролей: {len(changes)}. Бэкап: {backup.name}")


@dataclass
class RoleResult:
    changed: bool
    message: str
