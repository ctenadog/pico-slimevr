"""Build a standalone Windows executable with PyInstaller.

Run on Windows:  python packaging/build.py
Output:          dist/pico-slimevr.exe
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "packaging" / "pico-slimevr.spec"


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller не установлен. Установите: pip install pyinstaller")
        return 1

    command = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"]
    print("Запуск:", " ".join(command))
    completed = subprocess.run(command, cwd=str(ROOT))
    if completed.returncode == 0:
        print("Готово: dist/pico-slimevr.exe")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
