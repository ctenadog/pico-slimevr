# Build with:  pyinstaller packaging/pico-slimevr.spec --noconfirm
# Produces dist/pico-slimevr.exe (one-file, GUI + CLI).

import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

a = Analysis(
    [str(ROOT / "src" / "pico_slimevr" / "cli.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=["pico_slimevr.gui", "pico_slimevr.osc", "pico_slimevr.trackers"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "pandas", "matplotlib", "PIL"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="pico-slimevr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)
