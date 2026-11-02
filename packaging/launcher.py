"""Frozen-app entry point.

PyInstaller runs this file as ``__main__`` with no parent package, so it must
import the real package by absolute name instead of using relative imports.
"""

from pico_slimevr.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
