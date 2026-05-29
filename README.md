# Dwell Clicker

A simple Windows app that clicks automatically when your cursor stays still.

## How to run

Double-click `launch.bat` or run:

```powershell
python dwell_clicker.py
```

## Features

- Enable/pause from the panel
- Global hotkey `F8` (customizable)
- Adjustable dwell time
- Adjustable movement tolerance
- Adjustable cooldown after click
- Left, right, or double click
- Circular indicator ring at cursor
- Customizable indicator color (Pro: 5 extra colors)
- Always-on cursor option (overrides sites that hide the cursor)
- Panel protection (panel itself is excluded from clicking)
- Windows 11 rounded corners, Mica backdrop, high-DPI support

## Note

This app uses the native Windows API to read cursor position and send clicks. It requires no internet connection and has no external dependencies.
