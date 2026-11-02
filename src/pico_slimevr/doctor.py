"""High level pipeline: scan, report, then optionally repair."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import actions, detect


@dataclass
class Report:
    env: detect.Environment
    checks: list[detect.Check]
    applied: list[actions.Action]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def scan(**kwargs) -> Report:
    env = detect.scan(**kwargs)
    return Report(env=env, checks=detect.checks(env), applied=[])


def run(fix: bool = False, dry_run: bool = False, **kwargs) -> Report:
    """Scan the machine and, when ``fix`` is set, apply the safe repairs."""
    env = detect.scan(**kwargs)
    applied: list[actions.Action] = []

    if fix:
        applied.append(actions.enable_body_tracking(env, dry_run=dry_run))
        applied.append(actions.register_slimevr_driver(env, dry_run=dry_run))

    checks = detect.checks(env)
    return Report(env=env, checks=checks, applied=applied)


def default_paths() -> dict[str, Path | None]:
    """Resolved paths, handy for printing and for the GUI."""
    env = detect.scan()
    return {
        "PICO Connect": env.pico_connect_dir,
        "PICO settings.json": env.pico_settings_file,
        "SteamVR": env.steamvr_dir,
        "SlimeVR": env.slimevr_dir,
        "SlimeVR driver": env.slimevr_driver_dir,
        "SlimeVR feeder": env.slimevr_feeder_exe,
    }
