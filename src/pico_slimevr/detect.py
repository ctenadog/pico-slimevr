"""Read-only inspection of the PICO Connect -> SteamVR -> SlimeVR pipeline.

Every check returns plain data so it can be unit tested against a fake filesystem
and rendered by both the CLI and the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import paths

# JSON profiles PICO Connect must expose for SteamVR to present ankle/waist/chest
# trackers. Missing ones are why games see no trackers even when the headset works.
SWIFT_PROFILE_FILES = [
    "legacy_bindings_vive_tracker_handed.json",
    "pico_tracker_camera_profile.json",
    "pico_tracker_chest_profile.json",
    "pico_tracker_keyboard_profile.json",
    "pico_tracker_left_foot_profile.json",
    "pico_tracker_left_knee_profile.json",
    "pico_tracker_left_shoulder_profile.json",
    "pico_tracker_right_foot_profile.json",
    "pico_tracker_right_knee_profile.json",
    "pico_tracker_right_shoulder_profile.json",
    "pico_tracker_waist_profile.json",
    "vive_tracker_handed_profile.json",
]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fixable: bool = False


@dataclass
class Environment:
    pico_connect_dir: Path | None = None
    pico_settings_file: Path | None = None
    pico_settings_data: dict | None = None
    pico_driver_input_dir: Path | None = None
    pico_swift_dir: Path | None = None
    pico_swift_missing: list[str] = field(default_factory=list)
    pico_tracker_profile: Path | None = None
    steamvr_dir: Path | None = None
    steamvr_drivers_dir: Path | None = None
    vrpathreg_exe: Path | None = None
    openvrpaths_file: Path | None = None
    openvr_external_drivers: list[str] = field(default_factory=list)
    slimevr_dir: Path | None = None
    slimevr_exe: Path | None = None
    slimevr_driver_dir: Path | None = None
    slimevr_feeder_exe: Path | None = None
    steamvr_driver_slimevr: Path | None = None


def _load_json(path: Path) -> dict | None:
    import json

    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _load_openvrpaths(path: Path) -> list[str]:
    import json

    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    drivers = data.get("external_drivers") if isinstance(data, dict) else None
    if not isinstance(drivers, list):
        return []
    return [str(item) for item in drivers]


def scan(
    *,
    program_roots: list[Path] | None = None,
    roaming: Path | None = None,
    local: Path | None = None,
    steam_roots: list[Path] | None = None,
) -> Environment:
    """Inspect the current machine without changing anything."""
    env = Environment()

    pico_dir = paths.pico_connect_dir(program_roots)
    if pico_dir is not None:
        env.pico_connect_dir = pico_dir
        env.pico_driver_input_dir = paths.pico_driver_input_dir(pico_dir)
        env.pico_tracker_profile = env.pico_driver_input_dir / "pico_tracker_profile.json"
        swift = env.pico_driver_input_dir / "swift"
        env.pico_swift_dir = swift
        if swift.is_dir():
            env.pico_swift_missing = [
                name for name in SWIFT_PROFILE_FILES if not (swift / name).is_file()
            ]
        else:
            env.pico_swift_missing = list(SWIFT_PROFILE_FILES)

    settings = paths.pico_connect_settings(roaming)
    if settings is not None:
        env.pico_settings_file = settings
        if settings.is_file():
            env.pico_settings_data = _load_json(settings)

    steamvr = paths.steamvr_dir(steam_roots)
    if steamvr is not None:
        env.steamvr_dir = steamvr
        env.steamvr_drivers_dir = paths.steamvr_drivers_dir(steamvr)
        env.vrpathreg_exe = paths.vrpathreg_exe(steamvr)
        env.steamvr_driver_slimevr = env.steamvr_drivers_dir / "slimevr"

    openvrpaths = paths.openvrpaths_file(local)
    if openvrpaths is not None:
        env.openvrpaths_file = openvrpaths
        if openvrpaths.is_file():
            env.openvr_external_drivers = _load_openvrpaths(openvrpaths)

    for candidate in paths.slimevr_dirs(local, program_roots):
        if candidate.is_dir():
            env.slimevr_dir = candidate
            break
    if env.slimevr_dir is not None:
        exe = env.slimevr_dir / "slimevr.exe"
        if not exe.is_file():
            exe = env.slimevr_dir / "SlimeVR.exe"
        env.slimevr_exe = exe if exe.is_file() else None
        feeder = env.slimevr_dir / "feeder" / "SlimeVR-Feeder-App.exe"
        if not feeder.is_file():
            feeder = env.slimevr_dir / "SlimeVR-Feeder-App.exe"
        env.slimevr_feeder_exe = feeder if feeder.is_file() else None
        driver = env.slimevr_dir / "slimevr"
        env.slimevr_driver_dir = driver if driver.is_dir() else None

    return env


def checks(env: Environment) -> list[Check]:
    """Turn a scanned environment into an ordered, human readable checklist."""
    result: list[Check] = []

    if env.pico_connect_dir is None:
        result.append(
            Check(
                "PICO Connect установлен",
                False,
                "Не найден в Program Files. Установите PICO Connect (стример с сайта PICO).",
            )
        )
    else:
        result.append(Check("PICO Connect установлен", True, str(env.pico_connect_dir)))

    if env.pico_settings_file is None:
        result.append(Check("PICO Connect: settings.json", False, "Путь APPDATA не определён."))
    elif not env.pico_settings_file.is_file():
        result.append(
            Check(
                "PICO Connect: settings.json",
                False,
                "Файл не найден. Запустите PICO Connect и войдите в аккаунт хотя бы раз.",
            )
        )
    else:
        value = None
        if isinstance(env.pico_settings_data, dict):
            value = env.pico_settings_data.get("bodyTracking")
        if value is True:
            result.append(Check("PICO Connect: bodyTracking включён", True, "bodyTracking = true"))
        else:
            result.append(
                Check(
                    "PICO Connect: bodyTracking включён",
                    False,
                    "Нужно включить передачу тела в SteamVR (bodyTracking = true).",
                    fixable=True,
                )
            )

    if env.pico_swift_dir is None:
        result.append(
            Check("Профили трекеров (swift)", False, "Каталог драйвера PICO Connect не найден.")
        )
    elif not env.pico_swift_dir.is_dir():
        result.append(
            Check(
                "Профили трекеров (swift)",
                False,
                "Каталог swift отсутствует — SteamVR не увидит ноги/пояс. "
                "Скопируйте профили вручную (см. README, раздел «Профили swift»).",
            )
        )
    elif env.pico_swift_missing:
        result.append(
            Check(
                "Профили трекеров (swift)",
                False,
                f"Не хватает {len(env.pico_swift_missing)} файл(ов) профилей. "
                "Скопируйте их вручную (см. README).",
            )
        )
    else:
        result.append(Check("Профили трекеров (swift)", True, "Все профили на месте."))

    if env.steamvr_dir is None:
        result.append(Check("SteamVR установлен", False, "Каталог SteamVR не найден."))
    else:
        result.append(Check("SteamVR установлен", True, str(env.steamvr_dir)))

    if env.vrpathreg_exe is None or not env.vrpathreg_exe.is_file():
        result.append(Check("SteamVR: vrpathreg доступен", False, "vrpathreg.exe не найден."))
    else:
        result.append(Check("SteamVR: vrpathreg доступен", True, str(env.vrpathreg_exe)))

    if env.slimevr_dir is None:
        result.append(
            Check(
                "SlimeVR Server установлен",
                False,
                "Не найден. Установите SlimeVR (installer) с slimevr.dev.",
            )
        )
    else:
        result.append(Check("SlimeVR Server установлен", True, str(env.slimevr_dir)))

    if env.slimevr_driver_dir is None:
        result.append(
            Check(
                "Драйвер SlimeVR для SteamVR",
                False,
                "Каталог slimevr рядом с сервером не найден — переустановите SlimeVR с галкой SteamVR.",
                fixable=True,
            )
        )
    else:
        result.append(Check("Драйвер SlimeVR для SteamVR", True, str(env.slimevr_driver_dir)))

    registered = _driver_registered(env)
    if registered is None:
        result.append(Check("Драйвер SlimeVR подключён к SteamVR", False, "Не удалось определить."))
    elif registered:
        result.append(
            Check("Драйвер SlimeVR подключён к SteamVR", True, "Драйвер зарегистрирован в openvrpaths.")
        )
    else:
        result.append(
            Check(
                "Драйвер SlimeVR подключён к SteamVR",
                False,
                "Драйвер не зарегистрирован. SteamVR не будет эмулировать трекеры SlimeVR.",
                fixable=True,
            )
        )

    if env.slimevr_feeder_exe is None:
        result.append(
            Check(
                "SlimeVR Feeder App",
                False,
                "Не найден. Без feeder-а SlimeVR не получит позиции Vive-трекеров от PICO.",
            )
        )
    else:
        result.append(Check("SlimeVR Feeder App", True, str(env.slimevr_feeder_exe)))

    return result


def _driver_registered(env: Environment) -> bool | None:
    if env.slimevr_driver_dir is None:
        return False
    target = str(env.slimevr_driver_dir).rstrip("\\/").lower()
    if env.steamvr_driver_slimevr is not None and env.steamvr_driver_slimevr.is_dir():
        return True
    for entry in env.openvr_external_drivers:
        if entry.rstrip("\\/").lower() == target:
            return True
    return False
