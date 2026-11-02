"""High level pipeline: scan, report, then optionally repair."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import actions, detect, osc, trackers


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
        role_result = trackers.apply_roles(env, dry_run=dry_run)
        applied.append(actions.Action("Роли трекеров в SteamVR", role_result.changed, role_result.message))

    checks = detect.checks(env)
    return Report(env=env, checks=checks, applied=applied)


def apply_roles(points: list[str] | None = None, dry_run: bool = False, **kwargs) -> Report:
    """Set tracker roles only, leaving the rest of the pipeline untouched."""
    env = detect.scan(**kwargs)
    result = trackers.apply_roles(env, points=points, dry_run=dry_run)
    return Report(
        env=env,
        checks=detect.checks(env),
        applied=[actions.Action("Роли трекеров в SteamVR", result.changed, result.message)],
    )


def uninstall(dry_run: bool = False, *, drop_backups: bool = False, **kwargs) -> Report:
    """Undo everything ``run(fix=True)`` changed, restoring original files."""
    env = detect.scan(**kwargs)
    applied: list[actions.Action] = []

    applied.append(actions.disable_body_tracking(env, dry_run=dry_run))
    applied.append(actions.unregister_slimevr_driver(env, dry_run=dry_run))
    role_result = trackers.revert_roles(env, dry_run=dry_run)
    applied.append(
        actions.Action("Роли трекеров в SteamVR", role_result.changed, role_result.message)
    )

    if drop_backups:
        for path in (env.pico_settings_file, env.openvrpaths_file, env.vrsettings_file):
            if path is None:
                continue
            if actions.drop_backup(path, dry_run=dry_run):
                applied.append(
                    actions.Action("Удалить бэкап", True, f"{actions._backup_of(path).name}")
                )

    return Report(env=env, checks=detect.checks(env), applied=applied)


def write_osc_profile(path: Path, **kwargs) -> Path:
    return osc.write_profile(path, **kwargs)


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
