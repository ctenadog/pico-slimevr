"""Tests run against real temp directories, not mocks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pico_slimevr import actions, detect  # noqa: E402
from pico_slimevr.detect import SWIFT_PROFILE_FILES  # noqa: E402


@pytest.fixture()
def fake_machine(tmp_path: Path):
    """Build a believable Windows layout inside a temp dir."""
    program = tmp_path / "Program Files"
    program_x86 = tmp_path / "Program Files (x86)"
    roaming = tmp_path / "Roaming"
    local = tmp_path / "Local"

    pico = program / "PICO Connect"
    (pico / "openvr_driver" / "resources" / "input" / "swift").mkdir(parents=True)
    (pico / "PICO Connect.exe").write_text("", encoding="utf-8")
    settings = roaming / "PICO Connect" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"bodyTracking": False}), encoding="utf-8")

    steamvr = program_x86 / "Steam" / "steamapps" / "common" / "SteamVR"
    (steamvr / "bin" / "win64").mkdir(parents=True)
    (steamvr / "bin" / "win64" / "vrpathreg.exe").write_text("", encoding="utf-8")

    openvrpaths = local / "openvr" / "openvrpaths.vrpath"
    openvrpaths.parent.mkdir(parents=True)
    openvrpaths.write_text(json.dumps({"external_drivers": []}), encoding="utf-8")

    slime = local / "Programs" / "SlimeVR"
    (slime / "feeder").mkdir(parents=True)
    (slime / "slimevr.exe").write_text("", encoding="utf-8")
    (slime / "feeder" / "SlimeVR-Feeder-App.exe").write_text("", encoding="utf-8")
    (slime / "slimevr").mkdir()

    return {
        "program": [program, program_x86],
        "roaming": roaming,
        "local": local,
        "steam_roots": [program_x86 / "Steam"],
        "pico_swift": pico / "openvr_driver" / "resources" / "input" / "swift",
        "settings": settings,
        "openvrpaths": openvrpaths,
        "slime_driver": slime / "slimevr",
    }


def test_scan_finds_components(fake_machine):
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    assert env.pico_connect_dir is not None
    assert env.steamvr_dir is not None
    assert env.slimevr_dir is not None
    assert env.slimevr_driver_dir == fake_machine["slime_driver"]
    assert env.slimevr_feeder_exe is not None


def test_checks_report_body_tracking_and_swift(fake_machine):
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    by_name = {c.name: c for c in detect.checks(env)}
    assert not by_name["PICO Connect: bodyTracking включён"].ok
    assert by_name["PICO Connect: bodyTracking включён"].fixable
    assert not by_name["Профили трекеров (swift)"].ok
    assert by_name["SlimeVR Server установлен"].ok
    assert not by_name["Драйвер SlimeVR подключён к SteamVR"].ok


def test_enable_body_tracking_writes_true_and_backup(fake_machine):
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    result = actions.enable_body_tracking(env)
    assert result.changed
    data = json.loads(fake_machine["settings"].read_text(encoding="utf-8"))
    assert data["bodyTracking"] is True
    assert fake_machine["settings"].with_suffix(".json.bak").is_file()


def test_enable_body_tracking_is_idempotent(fake_machine):
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    actions.enable_body_tracking(env)
    again = actions.enable_body_tracking(env)
    assert not again.changed


def test_register_driver_falls_back_to_openvrpaths(fake_machine, monkeypatch):
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    # Make vrpathreg unavailable so the fallback path runs.
    env.vrpathreg_exe = None
    result = actions.register_slimevr_driver(env)
    assert result.changed
    data = json.loads(fake_machine["openvrpaths"].read_text(encoding="utf-8"))
    assert str(fake_machine["slime_driver"]) in data["external_drivers"]
    assert fake_machine["openvrpaths"].with_suffix(".vrpath.bak").is_file()


def test_register_driver_is_idempotent(fake_machine):
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    env.vrpathreg_exe = None
    actions.register_slimevr_driver(env)
    again = actions.register_slimevr_driver(env)
    assert not again.changed


def test_dry_run_changes_nothing(fake_machine):
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    env.vrpathreg_exe = None
    result = actions.enable_body_tracking(env, dry_run=True)
    assert result.changed
    data = json.loads(fake_machine["settings"].read_text(encoding="utf-8"))
    assert data["bodyTracking"] is False


def test_full_repair_then_all_ok(fake_machine):
    from pico_slimevr import doctor

    kwargs = dict(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    report = doctor.run(fix=True, **kwargs)
    # The swift profiles are intentionally left for manual copying.
    remaining = {c.name for c in report.checks if not c.ok}
    assert remaining == {"Профили трекеров (swift)"}


def test_swift_profiles_recognised_when_present(fake_machine):
    swift = fake_machine["pico_swift"]
    for name in SWIFT_PROFILE_FILES:
        (swift / name).write_text("{}", encoding="utf-8")
    env = detect.scan(
        program_roots=fake_machine["program"],
        roaming=fake_machine["roaming"],
        local=fake_machine["local"],
        steam_roots=fake_machine["steam_roots"],
    )
    by_name = {c.name: c for c in detect.checks(env)}
    assert by_name["Профили трекеров (swift)"].ok
