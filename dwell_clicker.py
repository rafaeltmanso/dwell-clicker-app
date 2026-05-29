import ctypes
import json
import math
import os
import platform
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import font as tkfont, simpledialog, ttk


user32 = ctypes.windll.user32
shcore = getattr(ctypes.windll, "shcore", None)
dwmapi = getattr(ctypes.windll, "dwmapi", None)

try:
    _win_ver = platform.version().split(".")
    IS_WIN11 = len(_win_ver) >= 3 and int(_win_ver[2]) >= 22000
except (ValueError, IndexError):
    IS_WIN11 = False


MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080


VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75,
    "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "F13": 0x7C, "F14": 0x7D, "F15": 0x7E, "F16": 0x7F, "F17": 0x80, "F18": 0x81,
    "F19": 0x82, "F20": 0x83, "F21": 0x84, "F22": 0x85, "F23": 0x86, "F24": 0x87,
}
VK_REVERSE = {v: k for k, v in VK_MAP.items()}


INDICATOR_COLORS = {
    "Blue": "#56a3ff",
    "Green": "#39d98a",
    "Purple": "#a78bfa",
    "Pink": "#f472b6",
    "Yellow": "#facc15",
    "Red": "#fb7185",
}

PRO_COLORS = {"Green", "Purple", "Pink", "Yellow", "Red"}


def is_pro() -> bool:
    """Check if pro.flag is present next to the exe or inside the bundled resources."""
    if getattr(sys, "frozen", False):
        # Check bundled resources first (set by PyInstaller --add-data)
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass and (Path(meipass) / "pro.flag").is_file():
            return True
        # Also check next to the exe on disk (user-placed flag)
        return Path(sys.executable).parent.joinpath("pro.flag").is_file()
    return Path(__file__).parent.joinpath("pro.flag").is_file()


def _profiles_path() -> Path:
    """Return the path to the profiles JSON file."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / "profiles.json"


def _default_profile() -> dict:
    """Return the default profile dict matching current DwellSettings defaults."""
    return {
        "name": "Default",
        "dwell_ms": 850,
        "tolerance_px": 18,
        "cooldown_ms": 650,
        "click_mode": "left",
        "visual_feedback": True,
        "indicator_color": "Blue",
        "hotkey_name": "F8",
        "hotkey_vk": 0x77,
        "always_show_cursor": False,
    }


def _load_profiles() -> dict:
    """Load profiles from JSON. Returns {profile_name: profile_dict}."""
    path = _profiles_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_profiles(profiles: dict) -> None:
    """Write profiles dict to JSON file."""
    path = _profiles_path()
    try:
        path.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


@dataclass
class DwellSettings:
    enabled: bool = False
    dwell_ms: int = 850
    tolerance_px: int = 18
    cooldown_ms: int = 650
    click_mode: str = "left"
    visual_feedback: bool = True
    indicator_color: str = "Blue"
    hotkey_vk: int = 0x77
    hotkey_name: str = "F8"
    always_show_cursor: bool = False


def set_dpi_awareness() -> None:
    try:
        if shcore:
            shcore.SetProcessDpiAwareness(2)
        else:
            user32.SetProcessDPIAware()
    except Exception:
        pass


def apply_dwm_effects(hwnd: int) -> None:
    if not IS_WIN11 or not dwmapi:
        return
    try:
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
            ctypes.sizeof(ctypes.c_int)
        )
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_MAINWINDOW = 2
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(ctypes.c_int(DWMSBT_MAINWINDOW)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        pass


def get_cursor_position() -> tuple[int, int]:
    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def send_click(mode: str) -> None:
    if mode == "right":
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        return

    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    if mode == "double":
        time.sleep(0.07)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


class CursorRing(tk.Toplevel):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "#ff00ff")
        self.configure(bg="#ff00ff")
        self.size = 46
        self.canvas = tk.Canvas(
            self,
            width=self.size,
            height=self.size,
            bg="#ff00ff",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.last_progress = -1.0
        self.last_active = False
        self.last_color = ""
        self.click_through_ready = False

    def make_click_through(self) -> None:
        if self.click_through_ready:
            return
        hwnd = self.winfo_id()
        styles = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)
        self.click_through_ready = True

    def show_at(self, x: int, y: int, progress: float, active: bool, color: str) -> None:
        progress = max(0.0, min(1.0, progress))
        self.geometry(f"{self.size}x{self.size}+{x - self.size // 2}+{y - self.size // 2}")
        self.lift()
        self.attributes("-topmost", True)

        if (
            abs(progress - self.last_progress) > 0.015
            or active != self.last_active
            or color != self.last_color
        ):
            self.canvas.delete("all")
            pad = 6
            accent = color if active else "#7d8797"
            self.canvas.create_oval(
                pad,
                pad,
                self.size - pad,
                self.size - pad,
                outline="#0b1020",
                width=6,
            )
            self.canvas.create_oval(
                pad + 2,
                pad + 2,
                self.size - pad - 2,
                self.size - pad - 2,
                outline="#dbeafe",
                width=2,
            )
            if progress > 0:
                self.canvas.create_arc(
                    pad,
                    pad,
                    self.size - pad,
                    self.size - pad,
                    start=90,
                    extent=-359 * progress,
                    style="arc",
                    outline=accent,
                    width=5,
                )
            self.last_progress = progress
            self.last_active = active
            self.last_color = color

        if not self.winfo_viewable():
            self.deiconify()
            self.after(0, self.make_click_through)

    def hide(self) -> None:
        if self.winfo_viewable():
            self.withdraw()


class DwellClickerApp:
    def __init__(self) -> None:
        set_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("Dwell Clicker")
        self.root.geometry("440x660")
        self.root.minsize(400, 600)
        self.root.configure(bg="#1a1a2e")
        self.root.after(50, lambda: apply_dwm_effects(int(self.root.winfo_id())))

        self.settings = DwellSettings()
        self.anchor_pos = get_cursor_position()
        self.anchor_time = time.perf_counter()
        self.last_click_time = 0.0
        self.waiting_for_movement = False
        self.grace_until = 0.0
        self.hotkey_was_down = False
        self.ring = CursorRing(self.root)

        self.enabled_var = tk.BooleanVar(value=self.settings.enabled)
        self.dwell_var = tk.IntVar(value=self.settings.dwell_ms)
        self.tolerance_var = tk.IntVar(value=self.settings.tolerance_px)
        self.cooldown_var = tk.IntVar(value=self.settings.cooldown_ms)
        self.click_mode_var = tk.StringVar(value=self.settings.click_mode)
        self.feedback_var = tk.BooleanVar(value=self.settings.visual_feedback)
        self.color_var = tk.StringVar(value=self.settings.indicator_color)
        self.status_var = tk.StringVar(value="Paused")
        self.detail_var = tk.StringVar(value=f"Enable when ready. {self.settings.hotkey_name} toggles quickly.")
        self.ring_test_var = tk.StringVar(value="")
        self.profile_status_var = tk.StringVar(value="")
        self.hotkey_var = tk.StringVar(value=self.settings.hotkey_name)
        self.always_cursor_var = tk.BooleanVar(value=self.settings.always_show_cursor)
        self.capturing_hotkey = False

        # Profile management (Pro only)
        self.profile_names: list[str] = []
        self.current_profile: str = "Default"
        self._load_profiles_ui()
        self.value_labels = [None, None, None]  # [dwell, tolerance, cooldown] labels

        self.configure_style()
        self.build_ui()
        # Re-apply profile now that combobox exists (ensures ring color is correct)
        self.root.after(0, lambda: self._apply_profile(self.current_profile))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Key>", self.on_key_press)
        self.root.after(16, self.tick)

        # ── Profile helpers ────────────────────────────────────────────────────

    def _load_profiles_ui(self) -> None:
        """Load profiles from disk and populate the profile selector."""
        profiles = _load_profiles()
        # Ensure Default always exists
        if "Default" not in profiles:
            profiles["Default"] = _default_profile()
            _save_profiles(profiles)
        self.profile_names = sorted(profiles.keys())
        # Load last-used profile or fall back to Default
        last = profiles.get("_last", {})
        self.current_profile = last.get("name", "Default")
        if self.current_profile not in self.profile_names:
            self.current_profile = "Default"
        self._apply_profile(self.current_profile)

    def _get_current_settings_dict(self) -> dict:
        """Snapshot current UI settings into a profile-ready dict."""
        return {
            "name": self.current_profile,
            "dwell_ms": int(self.dwell_var.get()),
            "tolerance_px": int(self.tolerance_var.get()),
            "cooldown_ms": int(self.cooldown_var.get()),
            "click_mode": self.click_mode_var.get(),
            "visual_feedback": bool(self.feedback_var.get()),
            "indicator_color": self.color_var.get(),
            "hotkey_name": self.settings.hotkey_name,
            "hotkey_vk": self.settings.hotkey_vk,
            "always_show_cursor": bool(self.always_cursor_var.get()),
        }

    def _apply_profile(self, name: str) -> None:
        """Load a profile's settings into the UI widgets."""
        profiles = _load_profiles()
        if name not in profiles:
            return
        p = profiles[name]
        self.current_profile = name

        self.dwell_var.set(p.get("dwell_ms", 850))
        self.tolerance_var.set(p.get("tolerance_px", 18))
        self.cooldown_var.set(p.get("cooldown_ms", 650))
        self.click_mode_var.set(p.get("click_mode", "left"))
        self.feedback_var.set(p.get("visual_feedback", True))
        # Enforce Blue for Free users
        color = p.get("indicator_color", "Blue")
        if not is_pro() and color not in ("Blue",):
            color = "Blue"
        self.color_var.set(color)
        self.settings.hotkey_name = p.get("hotkey_name", "F8")
        self.settings.hotkey_vk = p.get("hotkey_vk", 0x77)
        self.hotkey_var.set(self.settings.hotkey_name)
        self.always_cursor_var.set(p.get("always_show_cursor", False))
        self.sync_settings()

        # Update combobox if available
        if hasattr(self, "profile_combo"):
            self.profile_combo["values"] = self.profile_names
            self.profile_combo.set(name)

        # Save last-used
        profiles["_last"] = p
        _save_profiles(profiles)

    def _save_profile(self, name: str | None = None) -> None:
        """Save current UI settings into the named profile (or current if None)."""
        target = name or self.current_profile
        profiles = _load_profiles()
        if target not in profiles:
            profiles[target] = _default_profile()
        profiles[target].update(self._get_current_settings_dict())
        profiles[target]["name"] = target
        self.current_profile = target
        profiles["_last"] = profiles[target]
        _save_profiles(profiles)
        self.profile_names = sorted(profiles.keys())
        if hasattr(self, "profile_combo"):
            self.profile_combo["values"] = self.profile_names
            self.profile_combo.set(target)
        if hasattr(self, "profile_status_var"):
            self.profile_status_var.set(f'Saved "{target}"')

    def _delete_profile(self) -> None:
        """Delete the currently selected profile after confirmation."""
        if self.current_profile == "Default":
            return
        name = self.current_profile
        profiles = _load_profiles()
        if name in profiles:
            del profiles[name]
            _save_profiles(profiles)
        self.profile_names = sorted(profiles.keys())
        self._apply_profile("Default")

    def _on_profile_select(self, event=None) -> None:
        """Called when user picks a profile from the dropdown."""
        if not hasattr(self, "profile_combo"):
            return
        selected = self.profile_combo.get()
        if selected in self.profile_names:
            self._apply_profile(selected)

    def _new_profile_dialog(self) -> None:
        """Prompt for a name and create a new profile copied from current."""
        name = simpledialog.askstring(
            "New Profile",
            "Profile name:",
            initialvalue="My Profile",
            parent=self.root,
        )
        if not name or not name.strip():
            return
        name = name.strip()
        profiles = _load_profiles()
        if name in profiles:
            name = f"{name} (2)"
        profiles[name] = self._get_current_settings_dict()
        profiles[name]["name"] = name
        _save_profiles(profiles)
        self.profile_names = sorted(profiles.keys())
        self._apply_profile(name)

    def configure_style(self) -> None:
        _family = "Segoe UI Variable Display" if IS_WIN11 else "Segoe UI"
        _family_text = "Segoe UI Variable Text" if IS_WIN11 else _family

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=_family_text, size=10)
        tkfont.nametofont("TkTextFont").configure(family=_family_text, size=10)
        tkfont.nametofont("TkHeadingFont").configure(family=_family, size=10)

        style = ttk.Style()
        style.theme_use("clam")

        # Base colors
        bg_dark = "#1a1a2e"
        bg_card = "#16213e"
        bg_elevated = "#0f3460"
        accent = "#00d9ff"
        accent_hover = "#00b8d9"
        text_primary = "#ffffff"
        text_secondary = "#a0aec0"
        border_color = "#2d3748"

        style.configure(".", font=(_family_text, 10), background=bg_dark, foreground=text_primary)

        # Card frame - rounded appearance
        style.configure("Card.TFrame",
            background=bg_card,
            relief="flat",
            borderwidth=0
        )

        # Labels
        style.configure("Title.TLabel",
            font=(_family, 28, "bold"),
            foreground=text_primary,
            background=bg_dark
        )
        style.configure("Subtitle.TLabel",
            font=(_family_text, 11),
            foreground=text_secondary,
            background=bg_dark
        )
        style.configure("Section.TLabel",
            font=(_family, 11, "semibold"),
            foreground=text_primary,
            background=bg_card,
            padding=(0, 8, 0, 12)
        )
        style.configure("SettingLabel.TLabel",
            font=(_family_text, 10),
            foreground=text_primary,
            background=bg_card
        )
        style.configure("Value.TLabel",
            font=(_family, 11, "bold"),
            foreground=accent,
            background=bg_card
        )

        # Modern toggle button with gradient feel
        style.configure(
            "Toggle.TButton",
            font=(_family, 11, "bold"),
            padding=(20, 12),
            background=accent,
            foreground="#0a0a0f",
            borderwidth=0,
            lightcolor=accent,
            darkcolor=accent_hover,
        )
        style.map(
            "Toggle.TButton",
            background=[
                ("active", accent_hover),
                ("pressed", "#0095b3"),
                ("disabled", "#4a5568")
            ]
        )
        style.configure(
            "ToggleActive.TButton",
            font=(_family, 11, "bold"),
            padding=(20, 12),
            background="#ef4444",
            foreground="#ffffff",
            borderwidth=0
        )
        style.map(
            "ToggleActive.TButton",
            background=[
                ("active", "#dc2626"),
                ("pressed", "#b91c1c")
            ]
        )

        # Segmented button group (like GNOME)
        style.configure(
            "Segment.TFrame",
            background=bg_elevated,
            relief="flat"
        )
        style.configure(
            "Segment.TRadiobutton",
            font=(_family_text, 10),
            background=bg_elevated,
            foreground=text_primary,
            focuscolor=bg_elevated,
            padding=(12, 8)
        )
        style.map(
            "Segment.TRadiobutton",
            background=[
                ("active", accent),
                ("pressed", accent_hover)
            ],
            foreground=[("active", "#0a0a0f")]
        )

        # Checkbox
        style.configure(
            "Modern.TCheckbutton",
            font=(_family_text, 10),
            background=bg_card,
            foreground=text_primary,
            focuscolor=bg_card,
            padding=(0, 8)
        )
        style.map(
            "Modern.TCheckbutton",
            background=[("active", bg_card)]
        )

        # Slider
        style.configure(
            "Modern.Horizontal.TScale",
            background=bg_card,
            troughcolor=bg_elevated,
            lightcolor=accent,
            darkcolor=accent,
            borderwidth=0,
            padding=0
        )

        # Combobox
        style.configure(
            "Modern.TCombobox",
            font=(_family_text, 10),
            fieldbackground=bg_elevated,
            background=bg_card,
            foreground=text_primary,
            arrowcolor=accent,
            bordercolor=border_color,
            lightcolor=border_color,
            darkcolor=border_color
        )
        style.map(
            "Modern.TCombobox",
            fieldcolor=[("focus", bg_elevated), ("!focus", bg_elevated)]
        )

        # Small button
        style.configure(
            "Small.TButton",
            font=(_family_text, 9),
            padding=(12, 6),
            background=bg_elevated,
            foreground=text_primary,
            borderwidth=0
        )
        style.map(
            "Small.TButton",
            background=[
                ("active", accent),
                ("pressed", accent_hover)
            ],
            foreground=[("active", "#0a0a0f")]
        )

    def build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=(28, 24))
        outer.pack(fill="both", expand=True)

        # Header
        header_frame = ttk.Frame(outer, style="Card.TFrame")
        header_frame.pack(anchor="w", fill="x", pady=(0, 4))
        title_label = ttk.Label(header_frame, text="Dwell Clicker", style="Title.TLabel")
        title_label.pack(side="left")

        if is_pro():
            pro_badge = tk.Label(
                header_frame,
                text="  Pro  ",
                font=("Segoe UI Variable Display", 10, "bold"),
                background="#a78bfa",
                foreground="#ffffff",
                padx=8,
                pady=2,
            )
            pro_badge.pack(side="left", padx=(10, 0))

        ttk.Label(
            outer,
            text="Click automatically when you hold your cursor still.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(8, 20))

        # Status card with modern toggle
        status_card = ttk.Frame(outer, style="Card.TFrame")
        status_card.pack(fill="x", pady=(0, 16))
        status_card.columnconfigure(0, weight=1)

        status_content = ttk.Frame(status_card, style="Card.TFrame")
        status_content.grid(row=0, column=0, padx=20, pady=16, sticky="ew")
        status_content.columnconfigure(0, weight=1)

        # Status indicator dot
        self.status_indicator = tk.Canvas(status_content, width=12, height=12,
            background="#1a1a2e", highlightthickness=0)
        self.status_indicator.create_oval(1, 1, 11, 11, fill="#4a5568", outline="")
        self.status_indicator.grid(row=0, column=0, sticky="w", pady=(0, 6))

        ttk.Label(status_content, textvariable=self.status_var, style="SettingLabel.TLabel").grid(
            row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(status_content, textvariable=self.detail_var,
            font=("Segoe UI Variable Text", 9), foreground="#a0aec0", background="#16213e").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.toggle_button = ttk.Button(
            status_card,
            text="Enable",
            style="Toggle.TButton",
            command=self.toggle_enabled,
        )
        self.toggle_button.grid(row=0, column=1, padx=(16, 20), pady=16, sticky="ns")

        # ── Profiles section (Pro only) ────────────────────────────────────────
        if is_pro():
            profiles_section = ttk.Frame(outer, style="Card.TFrame")
            profiles_section.pack(fill="x", pady=(0, 8))
            profiles_section.columnconfigure(0, weight=1)

            header = ttk.Frame(profiles_section, style="Card.TFrame")
            header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 4))
            ttk.Label(header, text="Profiles", style="Section.TLabel").pack(side="left")

            row = ttk.Frame(profiles_section, style="Card.TFrame")
            row.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
            row.columnconfigure(0, weight=1)

            self.profile_combo = ttk.Combobox(
                row,
                textvariable=tk.StringVar(value=self.current_profile),
                values=self.profile_names,
                state="readonly",
                width=18,
                style="Modern.TCombobox",
                font=("Segoe UI Variable Text", 10),
            )
            self.profile_combo.set(self.current_profile)
            self.profile_combo.pack(side="left")
            self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_select)

            ttk.Button(
                row, text="New", style="Small.TButton", width=5,
                command=self._new_profile_dialog,
            ).pack(side="left", padx=(6, 0))

            ttk.Button(
                row, text="Delete", style="Small.TButton", width=6,
                command=self._delete_profile,
            ).pack(side="left", padx=(4, 0))

            ttk.Button(
                row, text="Save", style="Small.TButton", width=5,
                command=lambda: self._save_profile(),
            ).pack(side="left", padx=(4, 0))

            status_lbl = ttk.Label(
                row, textvariable=self.profile_status_var,
                font=("Segoe UI Variable Text", 8),
                foreground="#39d98a", background="#16213e",
            )
            status_lbl.pack(side="left", padx=(8, 0))
        else:
            # Free paywall nudge
            lock_row = ttk.Frame(outer, style="Card.TFrame")
            lock_row.pack(fill="x", pady=(0, 8))
            ttk.Label(
                lock_row,
                text="\uD83D\uDD12 Save and switch between custom profiles  \u2192  dwellclicker.gumroad.com",
                font=("Segoe UI Variable Text", 9),
                foreground="#a78bfa",
                background="#16213e",
                padding=(20, 10),
                anchor="w",
            ).pack(fill="x")
            lock_row.bind("<Button-1>",
                lambda _: os.startfile("https://dwellclicker.gumroad.com/l/dwell-clicker-pro"))
            for child in lock_row.winfo_children():
                child.bind("<Button-1>",
                    lambda _: os.startfile("https://dwellclicker.gumroad.com/l/dwell-clicker-pro"))

        # Settings card
        settings_card = ttk.Frame(outer, style="Card.TFrame")
        settings_card.pack(fill="both", expand=True)
        settings_card.columnconfigure(0, weight=1)

        # Dwell Time Section  (shifted from row 0 → 2; add +2 to all existing row= params below)
        ttk.Label(settings_card, text="Timing", style="Section.TLabel").grid(
            row=2, column=0, sticky="ew", padx=20, pady=(20, 0))

        dwell_frame = ttk.Frame(settings_card, style="Card.TFrame")
        dwell_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.add_modern_slider(
            dwell_frame, row=0,
            label="Dwell time",
            variable=self.dwell_var,
            from_=250, to=2200, suffix="ms",
            command=self.sync_settings,
            label_index=0
        )

        # Tolerance Section
        ttk.Label(settings_card, text="Movement", style="Section.TLabel").grid(
            row=4, column=0, sticky="ew", padx=20)

        tolerance_frame = ttk.Frame(settings_card, style="Card.TFrame")
        tolerance_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.add_modern_slider(
            tolerance_frame, row=0,
            label="Movement tolerance",
            variable=self.tolerance_var,
            from_=4, to=48, suffix="px",
            command=self.sync_settings,
            label_index=1
        )

        # Cooldown Section
        ttk.Label(settings_card, text="Cooldown", style="Section.TLabel").grid(
            row=6, column=0, sticky="ew", padx=20)

        cooldown_frame = ttk.Frame(settings_card, style="Card.TFrame")
        cooldown_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.add_modern_slider(
            cooldown_frame, row=0,
            label="Cooldown after click",
            variable=self.cooldown_var,
            from_=150, to=1800, suffix="ms",
            command=self.sync_settings,
            label_index=2
        )

        # Click Mode - GNOME style segmented control
        ttk.Label(settings_card, text="Click mode", style="Section.TLabel").grid(
            row=8, column=0, sticky="ew", padx=20, pady=(8, 0))

        modes_frame = ttk.Frame(settings_card, style="Card.TFrame")
        modes_frame.grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 16))
        modes_frame.columnconfigure((0, 1, 2), weight=1)

        click_options = [
            ("Left", "left"),
            ("Right", "right"),
            ("Double", "double")
        ]

        for idx, (text, value) in enumerate(click_options):
            btn_frame = ttk.Frame(modes_frame, style="Segment.TFrame")
            btn_frame.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 4, 0 if idx == 2 else 4))

            rb = ttk.Radiobutton(
                btn_frame,
                text=text,
                value=value,
                variable=self.click_mode_var,
                style="Segment.TRadiobutton",
                command=self.sync_settings,
            )
            rb.pack(fill="both", expand=True, padx=2, pady=2)

        # Visual feedback toggle
        feedback_frame = ttk.Frame(settings_card, style="Card.TFrame")
        feedback_frame.grid(row=10, column=0, sticky="ew", padx=20, pady=(8, 0))

        ttk.Checkbutton(
            feedback_frame,
            text="Show circular indicator at cursor",
            variable=self.feedback_var,
            style="Modern.TCheckbutton",
            command=self.sync_settings,
        ).pack(side="left")

        ttk.Checkbutton(
            feedback_frame,
            text="Always show cursor (even on sites that hide it)",
            variable=self.always_cursor_var,
            style="Modern.TCheckbutton",
            command=self.sync_settings,
        ).pack(side="left", padx=(16, 0))


        # Color picker row
        color_frame = ttk.Frame(settings_card, style="Card.TFrame")
        color_frame.grid(row=11, column=0, sticky="ew", padx=20, pady=(16, 0))
        color_frame.columnconfigure(0, weight=1)
        color_frame.columnconfigure(1, weight=0)

        self.color_label = ttk.Label(color_frame, text="Indicator color", style="SettingLabel.TLabel")
        self.color_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        available_colors = list(INDICATOR_COLORS.keys()) if is_pro() else ["Blue"]
        if not is_pro():
            self.color_var.set("Blue")

        color_picker = ttk.Combobox(
            color_frame,
            textvariable=self.color_var,
            values=available_colors,
            state="readonly",
            width=14,
            style="Modern.TCombobox",
            font=("Segoe UI Variable Text", 10)
        )
        color_picker.grid(row=0, column=1, sticky="e")
        color_picker.bind("<<ComboboxSelected>>", lambda _event: self.sync_settings())

        # Paywall nudge for Free users
        if not is_pro():
            self.color_pro_nudge = ttk.Frame(color_frame, style="Card.TFrame")
            self.color_pro_nudge.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
            ttk.Label(
                self.color_pro_nudge,
                text="\uD83D\uDD12 Pro unlocks 5 more colors",
                font=("Segoe UI Variable Text", 8),
                foreground="#a78bfa",
                background="#16213e"
            ).pack(side="left")
            ttk.Label(
                self.color_pro_nudge,
                text=" \u2192 ",
                font=("Segoe UI Variable Text", 8),
                foreground="#4a5568",
                background="#16213e"
            ).pack(side="left")
            pro_link = tk.Label(
                self.color_pro_nudge,
                text="dwellclicker.gumroad.com",
                font=("Segoe UI Variable Text", 8),
                foreground="#a78bfa",
                background="#16213e",
                cursor="hand2"
            )
            pro_link.pack(side="left")
            pro_link.bind("<Button-1>",
                lambda _: os.startfile("https://dwellclicker.gumroad.com/l/dwell-clicker-pro"))

        # Hotkey section
        hotkey_section = ttk.Frame(settings_card, style="Card.TFrame")
        hotkey_section.grid(row=12, column=0, sticky="ew", padx=20, pady=(8, 0))
        hotkey_section.columnconfigure(0, weight=1)

        ttk.Label(hotkey_section, text="Hotkey", style="Section.TLabel").grid(
            row=0, column=0, sticky="w")

        hotkey_row = ttk.Frame(hotkey_section, style="Card.TFrame")
        hotkey_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        hotkey_row.columnconfigure(0, weight=1)

        ttk.Label(hotkey_row, text="Shortcut key", style="SettingLabel.TLabel").grid(
            row=0, column=0, sticky="w")

        self.hotkey_btn = ttk.Button(
            hotkey_row,
            textvariable=self.hotkey_var,
            style="Small.TButton",
            width=10,
            command=self.start_hotkey_capture,
        )
        self.hotkey_btn.grid(row=0, column=1, sticky="e")

        # Preview button
        preview_frame = ttk.Frame(settings_card, style="Card.TFrame")
        preview_frame.grid(row=13, column=0, sticky="w", padx=20, pady=(16, 20))

        ttk.Button(
            preview_frame,
            text="Test indicator",
            style="Small.TButton",
            command=self.preview_ring,
        ).pack(side="left")

        ttk.Label(preview_frame, textvariable=self.ring_test_var,
            font=("Segoe UI Variable Text", 9), foreground="#a0aec0",
            background="#16213e").pack(side="left", padx=(12, 0))

        # Footer tip
        self.footer = ttk.Label(
            outer,
            text=f"Tip: {self.settings.hotkey_name} pauses or enables without returning to the panel.",
            style="Subtitle.TLabel",
        )
        self.footer.pack(anchor="w", pady=(16, 0))

    def add_modern_slider(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.IntVar,
        from_: int,
        to: int,
        suffix: str,
        command,
        label_index: int = -1,
    ) -> None:
        # Header row with label and current value
        header = ttk.Frame(parent, style="Card.TFrame")
        header.pack(fill="x", pady=(8, 4))

        ttk.Label(header, text=label, style="SettingLabel.TLabel").pack(side="left")

        value_label = ttk.Label(header, text="", style="Value.TLabel")
        value_label.pack(side="right")

        # Store label for later updates
        if label_index >= 0 and label_index < len(self.value_labels):
            self.value_labels[label_index] = value_label

        def update_label(*_args) -> None:
            value_label.configure(text=f"{variable.get()} {suffix}")

        variable.trace_add("write", update_label)
        update_label()

        # Modern slider
        scale = ttk.Scale(
            parent,
            from_=from_,
            to=to,
            variable=variable,
            orient="horizontal",
            style="Modern.Horizontal.TScale",
            command=lambda _value: command(),
        )
        scale.pack(fill="x", pady=(0, 8))

        # Min/Max labels below slider
        scale_footer = ttk.Frame(parent, style="Card.TFrame")
        scale_footer.pack(fill="x")
        ttk.Label(scale_footer, text=str(from_), font=("Segoe UI Variable Text", 8),
            foreground="#718096", background="#16213e").pack(side="left")
        ttk.Label(scale_footer, text=str(to), font=("Segoe UI Variable Text", 8),
            foreground="#718096", background="#16213e").pack(side="right")

    def sync_settings(self) -> None:
        self.settings.dwell_ms = int(self.dwell_var.get())
        self.settings.tolerance_px = int(self.tolerance_var.get())
        self.settings.cooldown_ms = int(self.cooldown_var.get())
        self.settings.click_mode = self.click_mode_var.get()
        self.settings.visual_feedback = self.feedback_var.get()
        # Enforce Blue color for Free users (safety net)
        chosen_color = self.color_var.get()
        self.settings.indicator_color = chosen_color if is_pro() else "Blue"
        if not is_pro() and chosen_color != "Blue":
            self.color_var.set("Blue")
        self.settings.always_show_cursor = self.always_cursor_var.get()

    def toggle_enabled(self) -> None:
        self.set_enabled(not self.settings.enabled)

    def set_enabled(self, enabled: bool) -> None:
        self.settings.enabled = enabled
        self.enabled_var.set(enabled)
        self.anchor_pos = get_cursor_position()
        self.anchor_time = time.perf_counter()
        self.last_click_time = 0.0
        self.waiting_for_movement = False
        self.grace_until = time.perf_counter() + 0.7
        self.status_var.set("Active" if enabled else "Paused")
        self.detail_var.set(
            "Move the cursor out of the panel and hold it still."
            if enabled
            else f"Enable when ready. {self.settings.hotkey_name} toggles quickly."
        )

        # Update button style based on state
        if enabled:
            self.toggle_button.configure(text="Pause", style="ToggleActive.TButton")
            self.status_indicator.itemconfig(1, fill="#00d9ff")  # Active cyan dot
        else:
            self.toggle_button.configure(text="Enable", style="Toggle.TButton")
            self.status_indicator.itemconfig(1, fill="#4a5568")  # Inactive gray dot

        if not enabled:
            self.ring.hide()

    def preview_ring(self) -> None:
        x, y = get_cursor_position()
        color = INDICATOR_COLORS.get(self.settings.indicator_color, "#56a3ff")
        self.ring.show_at(x, y, 0.75, True, color)
        self.ring_test_var.set("Indicator shown around cursor for 2 seconds.")
        self.root.after(2000, self.ring.hide)
        self.root.after(2200, lambda: self.ring_test_var.set(""))

    def tick(self) -> None:
        self.handle_hotkey()
        self.sync_settings()

        x, y = get_cursor_position()
        now = time.perf_counter()
        dwell_seconds = self.settings.dwell_ms / 1000
        cooldown_seconds = self.settings.cooldown_ms / 1000
        distance = math.dist((x, y), self.anchor_pos)

        if distance > self.settings.tolerance_px:
            self.anchor_pos = (x, y)
            self.anchor_time = now
            self.waiting_for_movement = False
            distance = 0

        progress = min(1.0, (now - self.anchor_time) / dwell_seconds)
        cooling_down = now - self.last_click_time < cooldown_seconds

        if self.settings.enabled and self.is_pointer_over_panel(x, y):
            self.anchor_pos = (x, y)
            self.anchor_time = now
            self.detail_var.set("Panel protected. Move cursor away to click.")
            self.ring.hide()
        elif self.settings.enabled and now < self.grace_until:
            self.anchor_pos = (x, y)
            self.anchor_time = now
            self.detail_var.set("Ready. Position cursor on target.")
            self.ring.hide()
        elif self.settings.enabled and self.waiting_for_movement:
            self.anchor_pos = (x, y)
            self.anchor_time = now
            self.detail_var.set("Click sent. Move cursor to arm next.")
        elif self.settings.enabled and not cooling_down:
            self.detail_var.set(f"Preparing click: {int(progress * 100)}%")
            if progress >= 1.0:
                send_click(self.settings.click_mode)
                self.last_click_time = time.perf_counter()
                self.anchor_pos = get_cursor_position()
                self.anchor_time = self.last_click_time
                self.waiting_for_movement = True
                self.detail_var.set("Click sent. Waiting for new movement.")
        elif self.settings.enabled and cooling_down:
            remaining = max(0, cooldown_seconds - (now - self.last_click_time))
            self.detail_var.set(f"Waiting {remaining:.1f}s before next click.")

        color = INDICATOR_COLORS.get(self.settings.indicator_color, "#56a3ff")

        if self.settings.enabled and self.settings.always_show_cursor and not self.is_pointer_over_panel(x, y):
            active = now >= self.grace_until and not self.waiting_for_movement and not cooling_down
            p = progress if active else 0
            self.ring.show_at(x, y, p, active, color)
        elif (
            self.settings.enabled
            and self.settings.visual_feedback
            and not self.is_pointer_over_panel(x, y)
            and now >= self.grace_until
            and not self.waiting_for_movement
        ):
            self.ring.show_at(x, y, 0 if cooling_down else progress, True, color)
        else:
            self.ring.hide()

        self.root.after(16, self.tick)

    def is_pointer_over_panel(self, x: int, y: int) -> bool:
        try:
            hwnd = self.root.winfo_id()
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return rect.left <= x <= rect.right and rect.top <= y <= rect.bottom
        except Exception:
            return False

    def start_hotkey_capture(self) -> None:
        self.capturing_hotkey = True
        self.hotkey_var.set("...")

    def on_key_press(self, event: tk.Event) -> None:
        if not self.capturing_hotkey:
            return
        self.capturing_hotkey = False

        name = event.keysym
        vk = VK_MAP.get(name)
        if vk is None:
            self.hotkey_var.set(self.settings.hotkey_name)
            return

        self.settings.hotkey_vk = vk
        self.settings.hotkey_name = name
        self.hotkey_var.set(name)
        self.footer.configure(
            text=f"Tip: {name} pauses or enables without returning to the panel."
        )

    def handle_hotkey(self) -> None:
        is_down = bool(user32.GetAsyncKeyState(self.settings.hotkey_vk) & 0x8000)
        if is_down and not self.hotkey_was_down:
            self.toggle_enabled()
        self.hotkey_was_down = is_down

    def close(self) -> None:
        self.ring.hide()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    DwellClickerApp().run()
