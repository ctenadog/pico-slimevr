"""Repair actions for the PICO Connect -> SteamVR -> SlimeVR pipeline.

Each function is idempotent and takes ``dry_run`` so the caller can preview
changes. Writes always keep a ``.bak`` copy of the original file.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .detect import Environment


@dataclass
class Action:
    title: str
    changed: bool
    message: str


def enable_body_tracking(env: Environment, *, dry_run: bool = False) -> Action:
    """Set ``bodyTracking = true`` in PICO Connect's settings.json."""
    path = env.pico_settings_file
    if path is None or not path.is_file():
        return Action("Включить bodyTracking", False, "settings.json PICO Connect не найден.")

    data = env.pico_settings_data
    if not isinstance(data, dict):
        return Action("Включить bodyTracking", False, "settings.json не читается как JSON.")

    if data.get("bodyTracking") is True:
        return Action("Включить bodyTracking", False, "Уже включено.")

    if dry_run:
        return Action("Включить bodyTracking", True, f"Будет изменён {path}")

    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    data["bodyTracking"] = True
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    env.pico_settings_data = data
    return Action("Включить bodyTracking", True, f"Включено. Бэкап: {backup.name}")


def register_slimevr_driver(env: Environment, *, dry_run: bool = False) -> Action:
    """Make SteamVR load the SlimeVR driver so it can emulate Vive trackers."""
    driver = env.slimevr_driver_dir
    if driver is None:
        return Action(
            "Подключить драйвер SlimeVR к SteamVR",
            False,
            "Каталог драйвера SlimeVR не найден.",
        )

    if env.steamvr_driver_slimevr is not None and env.steamvr_driver_slimevr.is_dir():
        return Action(
            "Подключить драйвер SlimeVR к SteamVR",
            False,
            "Уже установлен в SteamVR/drivers/slimevr.",
        )

    if dry_run:
        return Action(
            "Подключить драйвер SlimeVR к SteamVR",
            True,
            f"Будет зарегистрирован {driver}",
        )

    if env.vrpathreg_exe is not None and env.vrpathreg_exe.is_file():
        try:
            completed = subprocess.run(
                [str(env.vrpathreg_exe), "adddriver", str(driver)],
                capture_output=True,
                text=True,
            )
        except OSError as error:
            completed = None
            stderr = str(error)
        else:
            stderr = completed.stderr.strip()
            if completed.returncode == 0:
                return Action(
                    "Подключить драйвер SlimeVR к SteamVR",
                    True,
                    "Зарегистрирован через vrpathreg.",
                )
        if _append_external_driver(env, driver):
            return Action(
                "Подключить драйвер SlimeVR к SteamVR",
                True,
                "vrpathreg не сработал, добавлено в openvrpaths.vrpath.",
            )
        return Action(
            "Подключить драйвер SlimeVR к SteamVR",
            False,
            f"vrpathreg недоступен или вернул ошибку: {stderr}",
        )

    if _append_external_driver(env, driver):
        return Action(
            "Подключить драйвер SlimeVR к SteamVR",
            True,
            "Добавлено в openvrpaths.vrpath.",
        )
    return Action(
        "Подключить драйвер SlimeVR к SteamVR",
        False,
        "Ни vrpathreg, ни openvrpaths.vrpath недоступны.",
    )


def _append_external_driver(env: Environment, driver: Path) -> bool:
    path = env.openvrpaths_file
    if path is None or not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False

    drivers = data.setdefault("external_drivers", [])
    if not isinstance(drivers, list):
        return False
    target = str(driver)
    if any(str(item).rstrip("\\/").lower() == target.rstrip("\\/").lower() for item in drivers):
        return False

    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    drivers.append(target)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    env.openvr_external_drivers = [str(item) for item in drivers]
    return True


def open_pico_connect(env: Environment, *, dry_run: bool = False) -> Action:
    if env.pico_connect_dir is None:
        return Action("Запустить PICO Connect", False, "PICO Connect не найден.")
    exe = _first_exe(
        env.pico_connect_dir,
        ["PICO Connect.exe", "PicoConnect.exe", "Pico Connect.exe"],
    )
    if exe is None:
        return Action("Запустить PICO Connect", False, "Исполняемый файл PICO Connect не найден.")
    return _launch("Запустить PICO Connect", exe, dry_run)


def open_slimevr(env: Environment, *, dry_run: bool = False) -> Action:
    if env.slimevr_exe is None:
        return Action("Запустить SlimeVR Server", False, "slimevr.exe не найден.")
    return _launch("Запустить SlimeVR Server", env.slimevr_exe, dry_run)


def _first_exe(directory: Path, names: list[str]) -> Path | None:
    for name in names:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    matches = sorted(directory.glob("*.exe"))
    return matches[0] if matches else None


def _backup_of(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".bak")


def restore_from_backup(path: Path, *, dry_run: bool) -> bool:
    """Copy ``path.bak`` back over ``path``. Returns False if no backup exists."""
    backup = _backup_of(path)
    if not backup.is_file():
        return False
    if not dry_run:
        shutil.copy2(backup, path)
    return True


def drop_backup(path: Path, *, dry_run: bool) -> bool:
    """Delete the ``.bak`` file once a revert is complete. Returns True if removed."""
    backup = _backup_of(path)
    if not backup.is_file():
        return False
    if not dry_run:
        backup.unlink()
    return True


def disable_body_tracking(env: Environment, *, dry_run: bool = False) -> Action:
    """Undo :func:`enable_body_tracking`.

    Prefers restoring the original file so unrelated settings survive exactly;
    falls back to setting ``bodyTracking = false`` when there is no backup.
    """
    title = "Отключить bodyTracking"
    path = env.pico_settings_file
    if path is None or not path.is_file():
        return Action(title, False, "settings.json PICO Connect не найден.")

    if _backup_of(path).is_file():
        if dry_run:
            return Action(title, True, f"Будет восстановлен {_backup_of(path).name}")
        restore_from_backup(path, dry_run=False)
        env.pico_settings_data = None
        return Action(title, True, f"Восстановлено из {_backup_of(path).name}")

    data = env.pico_settings_data
    if not isinstance(data, dict):
        return Action(title, False, "settings.json не читается как JSON.")
    if data.get("bodyTracking") is not True:
        return Action(title, False, "Уже выключено.")

    if dry_run:
        return Action(title, True, "bodyTracking будет выставлен в false")

    data["bodyTracking"] = False
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    env.pico_settings_data = data
    return Action(title, True, "bodyTracking = false")


def unregister_slimevr_driver(env: Environment, *, dry_run: bool = False) -> Action:
    """Undo :func:`register_slimevr_driver`."""
    title = "Отключить драйвер SlimeVR от SteamVR"
    driver = env.slimevr_driver_dir
    if driver is None:
        return Action(title, False, "Каталог драйвера SlimeVR не найден.")

    removed_paths: list[str] = []
    if env.vrpathreg_exe is not None and env.vrpathreg_exe.is_file():
        if not dry_run:
            try:
                completed = subprocess.run(
                    [str(env.vrpathreg_exe), "removedriver", str(driver)],
                    capture_output=True,
                    text=True,
                )
                if completed.returncode == 0:
                    removed_paths.append("vrpathreg")
            except OSError:
                pass
        else:
            removed_paths.append("vrpathreg")

    if _remove_external_driver(env, driver, dry_run=dry_run):
        removed_paths.append("openvrpaths.vrpath")

    if not removed_paths:
        return Action(title, False, "Драйвер не был зарегистрирован.")
    return Action(title, True, "Убрано из: " + ", ".join(removed_paths))


def _remove_external_driver(env: Environment, driver: Path, *, dry_run: bool) -> bool:
    path = env.openvrpaths_file
    if path is None or not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False

    drivers = data.get("external_drivers")
    if not isinstance(drivers, list):
        return False
    target = str(driver).rstrip("\\/").lower()
    kept = [item for item in drivers if str(item).rstrip("\\/").lower() != target]
    if len(kept) == len(drivers):
        return False

    if dry_run:
        return True
    data["external_drivers"] = kept
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    env.openvr_external_drivers = [str(item) for item in kept]
    return True


def _launch(title: str, exe: Path, dry_run: bool) -> Action:
    if dry_run:
        return Action(title, True, f"Будет запущен {exe.name}")
    try:
        subprocess.Popen([str(exe)], cwd=str(exe.parent))
    except OSError as error:
        return Action(title, False, f"Не удалось запустить: {error}")
    return Action(title, True, f"Запущен {exe.name}")
