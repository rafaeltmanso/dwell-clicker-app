import ctypes
import math
import platform
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont, ttk


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
VK_F8 = 0x77
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080


INDICATOR_COLORS = {
    "Azul": "#56a3ff",
    "Verde": "#39d98a",
    "Roxo": "#a78bfa",
    "Rosa": "#f472b6",
    "Amarelo": "#facc15",
    "Vermelho": "#fb7185",
}


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
    indicator_color: str = "Azul"


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
        self.root.geometry("440x620")
        self.root.minsize(400, 560)
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
        self.status_var = tk.StringVar(value="Pausado")
        self.detail_var = tk.StringVar(value="Ative quando estiver pronto. F8 alterna rápido.")
        self.ring_test_var = tk.StringVar(value="")
        self.value_labels = []  # Store value labels for each slider [dwell, tolerance, cooldown]

        self.configure_style()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(16, self.tick)

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
        ttk.Label(outer, text="Dwell Clicker", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Clique automaticamente ao manter o cursor parado.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 20))

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
            text="Ativar",
            style="Toggle.TButton",
            command=self.toggle_enabled,
        )
        self.toggle_button.grid(row=0, column=1, padx=(16, 20), pady=16, sticky="ns")

        # Settings card
        settings_card = ttk.Frame(outer, style="Card.TFrame")
        settings_card.pack(fill="both", expand=True)
        settings_card.columnconfigure(0, weight=1)

        # Dwell Time Section
        ttk.Label(settings_card, text="Tempo", style="Section.TLabel").grid(
            row=0, column=0, sticky="ew", padx=20, pady=(20, 0))

        dwell_frame = ttk.Frame(settings_card, style="Card.TFrame")
        dwell_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.add_modern_slider(
            dwell_frame, row=0,
            label="Tempo parado",
            variable=self.dwell_var,
            from_=250, to=2200, suffix="ms",
            command=self.sync_settings,
            label_index=0
        )

        # Tolerance Section
        ttk.Label(settings_card, text="Movimento", style="Section.TLabel").grid(
            row=2, column=0, sticky="ew", padx=20)

        tolerance_frame = ttk.Frame(settings_card, style="Card.TFrame")
        tolerance_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.add_modern_slider(
            tolerance_frame, row=0,
            label="Tolerância de movimento",
            variable=self.tolerance_var,
            from_=4, to=48, suffix="px",
            command=self.sync_settings,
            label_index=1
        )

        # Cooldown Section
        ttk.Label(settings_card, text="Intervalo", style="Section.TLabel").grid(
            row=4, column=0, sticky="ew", padx=20)

        cooldown_frame = ttk.Frame(settings_card, style="Card.TFrame")
        cooldown_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.add_modern_slider(
            cooldown_frame, row=0,
            label="Intervalo após clique",
            variable=self.cooldown_var,
            from_=150, to=1800, suffix="ms",
            command=self.sync_settings,
            label_index=2
        )

        # Click Mode - GNOME style segmented control
        ttk.Label(settings_card, text="Tipo de clique", style="Section.TLabel").grid(
            row=6, column=0, sticky="ew", padx=20, pady=(8, 0))

        modes_frame = ttk.Frame(settings_card, style="Card.TFrame")
        modes_frame.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 16))
        modes_frame.columnconfigure((0, 1, 2), weight=1)

        click_options = [
            ("Esquerdo", "left"),
            ("Direito", "right"),
            ("Duplo", "double")
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
        feedback_frame.grid(row=8, column=0, sticky="ew", padx=20, pady=(8, 0))

        ttk.Checkbutton(
            feedback_frame,
            text="Mostrar indicador circular no cursor",
            variable=self.feedback_var,
            style="Modern.TCheckbutton",
            command=self.sync_settings,
        ).pack(side="left")

        # Color picker row
        color_frame = ttk.Frame(settings_card, style="Card.TFrame")
        color_frame.grid(row=9, column=0, sticky="ew", padx=20, pady=(16, 0))
        color_frame.columnconfigure(0, weight=1)
        color_frame.columnconfigure(1, weight=0)

        ttk.Label(color_frame, text="Cor do indicador", style="SettingLabel.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8))

        color_picker = ttk.Combobox(
            color_frame,
            textvariable=self.color_var,
            values=list(INDICATOR_COLORS.keys()),
            state="readonly",
            width=14,
            style="Modern.TCombobox",
            font=("Segoe UI Variable Text", 10)
        )
        color_picker.grid(row=0, column=1, sticky="e")
        color_picker.bind("<<ComboboxSelected>>", lambda _event: self.sync_settings())

        # Preview button
        preview_frame = ttk.Frame(settings_card, style="Card.TFrame")
        preview_frame.grid(row=10, column=0, sticky="w", padx=20, pady=(16, 20))

        ttk.Button(
            preview_frame,
            text="Testar indicador",
            style="Small.TButton",
            command=self.preview_ring,
        ).pack(side="left")

        ttk.Label(preview_frame, textvariable=self.ring_test_var,
            font=("Segoe UI Variable Text", 9), foreground="#a0aec0",
            background="#16213e").pack(side="left", padx=(12, 0))

        # Footer tip
        footer = ttk.Label(
            outer,
            text="Dica: F8 pausa ou ativa sem precisar voltar ao painel.",
            style="Subtitle.TLabel",
        )
        footer.pack(anchor="w", pady=(16, 0))

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
        self.settings.indicator_color = self.color_var.get()
        if not self.settings.visual_feedback:
            self.ring.hide()

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
        self.status_var.set("Ativo" if enabled else "Pausado")
        self.detail_var.set(
            "Mova o cursor para fora do painel e mantenha parado."
            if enabled
            else "Ative quando estiver pronto. F8 alterna rápido."
        )

        # Update button style based on state
        if enabled:
            self.toggle_button.configure(text="Pausar", style="ToggleActive.TButton")
            self.status_indicator.itemconfig(1, fill="#00d9ff")  # Active cyan dot
        else:
            self.toggle_button.configure(text="Ativar", style="Toggle.TButton")
            self.status_indicator.itemconfig(1, fill="#4a5568")  # Inactive gray dot

        if not enabled:
            self.ring.hide()

    def preview_ring(self) -> None:
        x, y = get_cursor_position()
        color = INDICATOR_COLORS.get(self.settings.indicator_color, "#56a3ff")
        self.ring.show_at(x, y, 0.75, True, color)
        self.ring_test_var.set("Indicador exibido em volta do cursor por 2 segundos.")
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
            self.detail_var.set("Painel protegido. Mova o cursor para fora para clicar.")
            self.ring.hide()
        elif self.settings.enabled and now < self.grace_until:
            self.anchor_pos = (x, y)
            self.anchor_time = now
            self.detail_var.set("Pronto. Posicione o cursor no alvo.")
            self.ring.hide()
        elif self.settings.enabled and self.waiting_for_movement:
            self.anchor_pos = (x, y)
            self.anchor_time = now
            self.detail_var.set("Clique enviado. Mova o cursor para armar o proximo.")
        elif self.settings.enabled and not cooling_down:
            self.detail_var.set(f"Preparando clique: {int(progress * 100)}%")
            if progress >= 1.0:
                send_click(self.settings.click_mode)
                self.last_click_time = time.perf_counter()
                self.anchor_pos = get_cursor_position()
                self.anchor_time = self.last_click_time
                self.waiting_for_movement = True
                self.detail_var.set("Clique enviado. Aguardando novo movimento.")
        elif self.settings.enabled and cooling_down:
            remaining = max(0, cooldown_seconds - (now - self.last_click_time))
            self.detail_var.set(f"Aguardando {remaining:.1f}s antes do proximo clique.")

        if (
            self.settings.enabled
            and self.settings.visual_feedback
            and not self.is_pointer_over_panel(x, y)
            and now >= self.grace_until
            and not self.waiting_for_movement
        ):
            color = INDICATOR_COLORS.get(self.settings.indicator_color, "#56a3ff")
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

    def handle_hotkey(self) -> None:
        is_down = bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
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
