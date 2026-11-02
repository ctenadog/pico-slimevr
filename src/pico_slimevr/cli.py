"""Command line entry point: ``pico-slimevr``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, doctor

_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"

EXPLAIN = """Как это всё работает

Протокол PICO-трекеров закрытый, поэтому данные с них нельзя читать напрямую.
Мы не пишем новый драйвер — мы правильно соединяем готовые звенья:

  PICO Motion Trackers (пояс + щиколотки)
        |  шлем PICO
        v
  PICO Connect (ПК)     -- отдаёт трекеры в SteamVR как эмулированные Vive-трекеры
        v
  SteamVR               -- видит их как Vive Tracker
        v
  SlimeVR Feeder App    -- забирает позиции из SteamVR
        v
  SlimeVR Server        -- считает скелет по пропорциям тела
        |-- SteamVR-драйвер SlimeVR  -> эмулирует Slime-трекеры в SteamVR
        |-- VRChat OSC               -> трекеры напрямую в VRChat

Что делает инструмент:

  pico-slimevr              проверить всю цепочку (ничего не меняет)
  pico-slimevr --fix        включить bodyTracking, подключить драйвер, выставить роли
  pico-slimevr --dry-run    показать, что будет изменено
  pico-slimevr --roles      выставить роли трекеров в SteamVR
  pico-slimevr --ports      проверить порты VRChat OSC (9000/9001)
  pico-slimevr --osc-profile FILE   сохранить шаблон настроек OSC
  pico-slimevr --uninstall  откатить всё, вернув файлы из бэкапов
  pico-slimevr --gui        графический интерфейс

Какие файлы меняются (каждый раз с копией .bak рядом):

  %APPDATA%\\PICO Connect\\settings.json          bodyTracking = true
  %LOCALAPPDATA%\\openvr\\openvrpaths.vrpath      путь к драйверу SlimeVR
  <Steam>\\config\\steamvr.vrsettings              роли трекеров (TrackerRole_*)

Откат: --uninstall возвращает эти файлы из .bak (или аккуратно отменяет правку,
если бэкапа нет). Флаг --purge-backups удаляет и сами .bak-файлы.

Чего инструмент не делает: не копирует профили swift (лицензия PICO),
не шьёт трекеры и не читает данные с них напрямую.
"""


def _supports_color() -> bool:
    return sys.stdout.isatty()


def _force_utf8_stdout() -> None:
    """Windows consoles default to cp1252; Russian output would crash."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def _mark(ok: bool) -> str:
    if not _supports_color():
        return "[OK]" if ok else "[!!]"
    return f"{_GREEN}[OK]{_RESET}" if ok else f"{_RED}[!!]{_RESET}"


def _render_actions(applied: list) -> None:
    if not applied:
        print("Нечего было менять.")
        return
    for action in applied:
        tag = "изменено" if action.changed else "пропущено"
        print(f"  - {action.title}: {tag} — {action.message}")


def _render(report: doctor.Report) -> None:
    print("Проверка цепочки PICO Motion Tracker -> SlimeVR\n")
    for check in report.checks:
        print(f"{_mark(check.ok)} {check.name}: {check.detail}")

    if report.applied:
        print("\nИзменения:")
        _render_actions(report.applied)

    print()
    if report.ok:
        print("Всё готово. Запустите SteamVR, затем SlimeVR Server.")
    else:
        problems = sum(1 for check in report.checks if not check.ok)
        print(f"Найдено проблем: {problems}. Запустите с --fix, чтобы починить автоматически.")
        print("Шаги, которые нужно сделать вручную, описаны в README.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pico-slimevr",
        description="Настройка PICO Motion Trackers для работы через SlimeVR Server.",
    )
    parser.add_argument("--fix", action="store_true", help="применить безопасные исправления")
    parser.add_argument("--dry-run", action="store_true", help="показать, что будет изменено")
    parser.add_argument("--json", action="store_true", help="вывести отчёт в JSON")
    parser.add_argument("--gui", action="store_true", help="открыть графический интерфейс")
    parser.add_argument(
        "--roles",
        nargs="?",
        const="",
        metavar="ТОЧКИ",
        help="выставить роли трекеров в SteamVR (например: WAIST,LEFT_FOOT,RIGHT_FOOT)",
    )
    parser.add_argument("--osc-profile", metavar="ФАЙЛ", help="записать шаблон VRChat OSC в файл")
    parser.add_argument("--ports", action="store_true", help="проверить порты VRChat OSC")
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="откатить все изменения (вернуть файлы из бэкапов)",
    )
    parser.add_argument(
        "--purge-backups",
        action="store_true",
        help="вместе с --uninstall удалить и файлы .bak",
    )
    parser.add_argument("--explain", action="store_true", help="как всё работает")
    parser.add_argument("--version", action="version", version=f"pico-slimevr {__version__}")
    args = parser.parse_args(argv)
    _force_utf8_stdout()

    if args.explain:
        print(EXPLAIN)
        return 0

    if args.gui:
        from .gui import run_gui

        return run_gui()

    if args.uninstall:
        report = doctor.uninstall(dry_run=args.dry_run, drop_backups=args.purge_backups)
        _render_actions(report.applied)
        print()
        print("Откат завершён. Перезапустите SteamVR." if not args.dry_run else "Это был предпросмотр (--dry-run).")
        return 0

    if args.osc_profile:
        path = doctor.write_osc_profile(Path(args.osc_profile))
        print(f"Шаблон OSC записан: {path}")
        return 0

    if args.ports:
        from . import osc

        for check in osc.check_ports():
            state = "свободен" if check.free else "занят"
            print(f"UDP {check.port}: {state} — {check.detail}")
        print("\nПравила firewall (запускать от администратора):")
        for command in osc.firewall_commands():
            print(f"  {command}")
        return 0

    if args.roles is not None:
        points = [p for p in args.roles.split(",") if p.strip()] or None
        report = doctor.apply_roles(points=points, dry_run=args.dry_run)
        for action in report.applied:
            tag = "изменено" if action.changed else "пропущено"
            print(f"{action.title}: {tag} — {action.message}")
        return 0 if all(c.ok for c in report.checks if "Роли" in c.name) else 1

    report = doctor.run(fix=args.fix, dry_run=args.dry_run)

    if args.json:
        import json

        payload = {
            "ok": report.ok,
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail, "fixable": c.fixable}
                for c in report.checks
            ],
            "applied": [
                {"title": a.title, "changed": a.changed, "message": a.message}
                for a in report.applied
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _render(report)

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
