# Repository notes for agents

## What this project is
`pico-slimevr` is a Windows-targeted setup/diagnostic tool that makes **PICO Motion
Trackers** work *through* **SlimeVR Server** (Slime-style FBT) rather than only as raw
Vive-tracker emulation in SteamVR.

## Key architectural fact
The PICO tracker protocol is closed. There is **no** way for third-party software to read
the trackers directly, so we do not write a tracker driver. Instead we wire up the existing
chain:

```
PICO trackers -> PICO Connect -> SteamVR (emulated Vive trackers)
             -> SlimeVR Feeder App -> SlimeVR Server -> SlimeVR driver / VRChat OSC
```

Anything that claims to "read Pico trackers directly" is wrong for this hardware.

## Code layout
- `src/pico_slimevr/paths.py` — path discovery (env-var driven, all overridable).
- `src/pico_slimevr/detect.py` — read-only `scan()` + `checks()`, returns dataclasses.
- `src/pico_slimevr/actions.py` — idempotent fixes; every write makes a `.bak`.
- `src/pico_slimevr/trackers.py` — SteamVR tracker roles in `steamvr.vrsettings`.
- `src/pico_slimevr/osc.py` — VRChat OSC profile + port checks (9000/9001).
- `src/pico_slimevr/doctor.py` — `scan()` / `run(fix=...)` / `apply_roles()`.
- `src/pico_slimevr/cli.py` / `gui.py` — entry points.
- `packaging/` — PyInstaller spec + `build.py`; CI in `.github/workflows/build.yml`.

## Conventions
- No third-party runtime dependencies (stdlib only); Tkinter is optional and imported lazily.
- Tests use real temp dirs via the `fake_machine` fixture, never mocks. Run: `python -m pytest -q`.
- `--fix` only does safe things: patch `bodyTracking`, register the SlimeVR driver, set tracker
  roles. The `swift` profile files are PICO-licensed and must be copied manually — do not bundle them.
- `--uninstall` reverses `--fix`: it restores the three touched files from their `.bak` copies
  (falling back to targeted in-place reversal when no backup exists). `--purge-backups` also
  deletes the `.bak` files. Any new fix action must ship a matching revert action.
- Tracker roles live in `<Steam>/config/steamvr.vrsettings` under a `trackers` object; device keys
  look like `/devices/SlimeVR/human://LEFT_FOOT` and values like `TrackerRole_LeftFoot`.
- All user-facing text is Russian.
