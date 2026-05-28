"""Build Dwell Clicker executables with PyInstaller.

Usage:
    python build.py              # build Pro for current platform
    python build.py --free       # build Free for current platform

Platform detection is automatic — produces .exe on Windows, .app on macOS.
"""

import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).parent
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def build(free: bool = False) -> None:
    suffix = "free" if free else "pro"
    pro_flag = HERE / "pro.flag"

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
    ]

    if IS_WIN:
        args.extend(["--onefile", "--noconsole"])
        out_name = f"dwell-clicker-{suffix}.exe"
    elif IS_MAC:
        args.extend(["--onedir", "--windowed", "--osx-bundle-identifier", "com.dwellclicker.app"])
        out_name = f"dwell-clicker-{suffix}.app"
    else:
        args.extend(["--onefile", "--noconsole"])
        out_name = f"dwell-clicker-{suffix}"

    args.extend([
        "--name", f"dwell-clicker-{suffix}",
        "--icon", str(HERE / "app.ico"),
        "--add-data", f"{HERE / 'app.ico'}{';' if IS_WIN else ':'}.",
    ])

    if not free:
        pro_flag.write_text("", encoding="utf-8")
        args.extend(["--add-data", f"{pro_flag}{';' if IS_WIN else ':'}."])

    if IS_MAC and not free:
        entitlements = HERE / "entitlements.plist"
        if entitlements.is_file():
            args.extend(["--osx-entitlements-file", str(entitlements)])

    args.append(str(HERE / "dwell_clicker.py"))

    print(f"Building {'Pro' if not free else 'Free'} for {sys.platform}...")
    subprocess.run(args, check=True)

    built = HERE / "dist" / out_name
    if built.is_file() or built.is_dir():
        size = built.stat().st_size if built.is_file() else _dir_size(built)
        print(f"Done: {built} ({size / 1024 / 1024:.1f} MB)")
    else:
        print("Build completed. Check dist/ directory.")


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


if __name__ == "__main__":
    build(free="--free" in sys.argv)
