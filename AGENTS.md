# Dwell Clicker App — Agent Guide

## What this is

Windows-only auto-clicker (Python 3.14, `tkinter` + `ctypes`). Single file, zero external dependencies — pure stdlib.

## Commands

```powershell
python dwell_clicker.py     # run with console window
pythonw dwell_clicker.py    # run without console (Windows)
launch.bat                  # shortcut for pythonw dwell_clicker.py
python build.py             # build Pro .exe with PyInstaller
python build.py --free      # build Free .exe
python make_icon.py         # regenerate app.ico
iscc installer.iss          # build Windows installer (requires Inno Setup)
```

No test/lint/typecheck system exists. No CI, no pre-commit, no formatter.

## Repo quirks

- **Two git repos**: main `.git/` (origin: `rafaeltmanso/dwell-clicker-app`) and `codex-git-store/` (backup, ignore)
- **`.gitignore`**: `__pycache__/`, `*.py[cod]`, `.venv/`, `codex-git-store/`, `dist/`, `build/`, `*.spec`, `pro.flag`
- **Main source**: `dwell_clicker.py` (~560 lines). Build tooling: `build.py`, `make_icon.py`, `app.ico`, `installer.iss`
- **No package manifest**, no `pyproject.toml`, no requirements. PyInstaller is the only build dependency.
- **Free/Pro model**: `is_pro()` checks for `pro.flag` next to the exe/source. Free = no restrictions (future use).

## Architecture

- `DwellSettings` dataclass holds all defaults: 850ms dwell, 18px tolerance, 650ms cooldown, left click, Azul indicator
- `INDICATOR_COLORS` dict maps color names to hex values — extension point for adding colors
- Everything runs in one `after(16, tick)` loop (~60 fps)
- DPI awareness via `shcore.SetProcessDpiAwareness(2)`
- `IS_WIN11` detection via `platform.version()` build number check (>= 22000)

### CursorRing

- `tk.Toplevel` with `overrideredirect(True)`, `-topmost`, `-transparentcolor "#ff00ff"`, `bg="#ff00ff"`
- `Canvas` draws concentric ovals + progress arc on transparent background
- `make_click_through()` sets `WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW` after first `deiconify()`
- Hotkey F8 via `GetAsyncKeyState` polling in `tick()`

### Windows 11 effects

- `_apply_dwm_effects(hwnd)` applies rounded corners (`DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2`) + Mica backdrop (`DWMWA_SYSTEMBACKDROP_TYPE = 38, DWMSBT_MAINWINDOW = 2`)
- Scheduled via `after(50, ...)` so DWM has a valid HWND
- Font: `Segoe UI Variable Display`/`Text` on Win 11, `Segoe UI` on older Windows

### Cursor / clicks

- `GetCursorPos` for position, `mouse_event` for clicks
- `ctypes` fast path consistently, no `pynput` dependency

## Key Windows APIs used

| API | Purpose |
|-----|---------|
| `GetCursorPos` | Cursor position |
| `mouse_event` | Left/right/double click |
| `GetAsyncKeyState` | F8 hotkey polling |
| `GetWindowRect` | Panel protection (prevent click on UI) |
| `SetWindowLongW` | Ring click-through (`WS_EX_TRANSPARENT`, `WS_EX_TOOLWINDOW`) |
| `attributes("-transparentcolor")` | Ring color-key transparency |
| `DwmSetWindowAttribute` | Win 11 rounded corners + Mica |
| `SetProcessDpiAwareness` | High-DPI support |

## What not to touch

- `codex-git-store/` — Codex internal backup, not part of the project
- `WS_EX_TRANSPARENT` / `WS_EX_TOOLWINDOW` on the ring window — required for click-through behavior
