"""Platform-aware lookup of the well-known Windows locations the pipeline lives in."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform.startswith("win")


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value)


def roaming_appdata() -> Path | None:
    return _env_path("APPDATA")


def local_appdata() -> Path | None:
    return _env_path("LOCALAPPDATA")


def program_files_roots() -> list[Path]:
    roots: list[Path] = []
    for name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        candidate = _env_path(name)
        if candidate and candidate not in roots:
            roots.append(candidate)
    return roots


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def pico_connect_dir(program_roots: list[Path] | None = None) -> Path | None:
    roots = program_roots if program_roots is not None else program_files_roots()
    candidates = [root / "PICO Connect" for root in roots]
    candidates += [root / "Pico Connect" for root in roots]
    return _first_existing(candidates)


def pico_connect_settings(roaming: Path | None = None) -> Path | None:
    base = roaming if roaming is not None else roaming_appdata()
    if base is None:
        return None
    return base / "PICO Connect" / "settings.json"


def pico_driver_input_dir(pico_dir: Path) -> Path:
    return pico_dir / "openvr_driver" / "resources" / "input"


def steamvr_dirs(steam_roots: list[Path] | None = None) -> list[Path]:
    roots = steam_roots if steam_roots is not None else _default_steam_roots()
    dirs: list[Path] = []
    override = _env_path("STEAMVR_PATH")
    if override:
        dirs.append(Path(override))
    for root in roots:
        dirs.append(root / "steamapps" / "common" / "SteamVR")
    return dirs


def _default_steam_roots() -> list[Path]:
    roots: list[Path] = []
    for base in program_files_roots():
        roots.append(base / "Steam")
    return roots


def steamvr_dir(steam_roots: list[Path] | None = None) -> Path | None:
    return _first_existing(steamvr_dirs(steam_roots))


def steam_config_dirs(steam_roots: list[Path] | None = None) -> list[Path]:
    """``<Steam>/config`` holds ``steamvr.vrsettings`` (tracker roles live here)."""
    roots = steam_roots if steam_roots is not None else _default_steam_roots()
    return [root / "config" for root in roots]


def steamvr_vrsettings(steam_roots: list[Path] | None = None) -> Path | None:
    """Return the vrsettings file if present, else the first plausible path."""
    candidates = [cfg / "steamvr.vrsettings" for cfg in steam_config_dirs(steam_roots)]
    existing = _first_existing(candidates)
    if existing is not None:
        return existing
    for candidate in candidates:
        if candidate.parent.is_dir():
            return candidate
    return None


def steamvr_drivers_dir(steamvr: Path) -> Path:
    return steamvr / "drivers"


def vrpathreg_exe(steamvr: Path) -> Path:
    return steamvr / "bin" / "win64" / "vrpathreg.exe"


def openvrpaths_file(local: Path | None = None) -> Path | None:
    base = local if local is not None else local_appdata()
    if base is None:
        return None
    return base / "openvr" / "openvrpaths.vrpath"


def slimevr_dirs(local: Path | None = None, program_roots: list[Path] | None = None) -> list[Path]:
    dirs: list[Path] = []
    base_local = local if local is not None else local_appdata()
    if base_local is not None:
        dirs.append(base_local / "Programs" / "SlimeVR")
    for root in program_roots if program_roots is not None else program_files_roots():
        dirs.append(root / "SlimeVR")
    return dirs
