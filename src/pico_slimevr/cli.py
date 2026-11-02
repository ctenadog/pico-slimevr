"""Command line entry point: ``pico-slimevr``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, doctor

_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _supports_color() -> bool:
    return sys.stdout.isatty()


def _mark(ok: bool) -> str:
    if not _supports_color():
        return "[OK]" if ok else "[!!]"
    return f"{_GREEN}[OK]{_RESET}" if ok else f"{_RED}[!!]{_RESET}"


def _render(report: doctor.Report) -> None:
    print("Проверка цепочки PICO Motion Tracker -> SlimeVR\n")
    for check in report.checks:
        print(f"{_mark(check.ok)} {check.name}: {check.detail}")

    if report.applied:
        print("\nИзменения:")
        for action in report.applied:
            tag = "изменено" if action.changed else "пропущено"
            print(f"  - {action.title}: {tag} — {action.message}")

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
    parser.add_argument("--version", action="version", version=f"pico-slimevr {__version__}")
    args = parser.parse_args(argv)

    if args.gui:
        from .gui import run_gui

        return run_gui()

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
