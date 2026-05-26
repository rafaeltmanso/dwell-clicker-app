import ctypes
import math
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk


user32 = ctypes.windll.user32
shcore = getattr(ctypes.windll, "shcore", None)


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
        self.root.geometry("430x560")
        self.root.minsize(390, 520)
        self.root.configure(bg="#0f1117")

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

        self.configure_style()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(16, self.tick)

    def configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#0f1117", foreground="#eef2ff")
        style.configure("TFrame", background="#0f1117")
        style.configure("Panel.TFrame", background="#171a23", relief="flat")
        style.configure("TLabel", background="#0f1117", foreground="#eef2ff")
        style.configure("Panel.TLabel", background="#171a23", foreground="#eef2ff")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), foreground="#f8fafc")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#a5adbd")
        style.configure("Status.TLabel", font=("Segoe UI Semibold", 12), foreground="#f8fafc")
        style.configure(
            "Accent.TButton",
            font=("Segoe UI Semibold", 11),
            padding=(16, 10),
            background="#2f80ed",
            foreground="#ffffff",
            bordercolor="#2f80ed",
            lightcolor="#2f80ed",
            darkcolor="#2f80ed",
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#56a3ff"), ("pressed", "#1f6fd1")],
            foreground=[("active", "#ffffff")],
        )
        style.configure(
            "TCheckbutton",
            background="#171a23",
            foreground="#eef2ff",
            focuscolor="#171a23",
        )
        style.map("TCheckbutton", background=[("active", "#171a23")])
        style.configure(
            "TRadiobutton",
            background="#171a23",
            foreground="#eef2ff",
            focuscolor="#171a23",
        )
        style.map("TRadiobutton", background=[("active", "#171a23")])
        style.configure(
            "Horizontal.TScale",
            background="#171a23",
            troughcolor="#2a3142",
            lightcolor="#56a3ff",
            darkcolor="#56a3ff",
        )
        style.configure(
            "TCombobox",
            fieldbackground="#0f1117",
            background="#171a23",
            foreground="#eef2ff",
            arrowcolor="#eef2ff",
            bordercolor="#2a3142",
            lightcolor="#2a3142",
            darkcolor="#2a3142",
        )

    def build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Dwell Clicker", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Clique automaticamente ao manter o cursor parado.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 18))

        status_panel = ttk.Frame(outer, style="Panel.TFrame", padding=18)
        status_panel.pack(fill="x", pady=(0, 14))
        status_panel.columnconfigure(0, weight=1)

        ttk.Label(status_panel, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(status_panel, textvariable=self.detail_var, style="Panel.TLabel").grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        self.toggle_button = ttk.Button(
            status_panel,
            text="Ativar",
            style="Accent.TButton",
            command=self.toggle_enabled,
        )
        self.toggle_button.grid(row=0, column=1, rowspan=2, padx=(16, 0), sticky="e")

        settings_panel = ttk.Frame(outer, style="Panel.TFrame", padding=18)
        settings_panel.pack(fill="both", expand=True)
        settings_panel.columnconfigure(0, weight=1)

        self.add_slider(
            settings_panel,
            row=0,
            label="Tempo parado",
            variable=self.dwell_var,
            from_=250,
            to=2200,
            suffix="ms",
            command=self.sync_settings,
        )
        self.add_slider(
            settings_panel,
            row=2,
            label="Tolerancia de movimento",
            variable=self.tolerance_var,
            from_=4,
            to=48,
            suffix="px",
            command=self.sync_settings,
        )
        self.add_slider(
            settings_panel,
            row=4,
            label="Intervalo apos clique",
            variable=self.cooldown_var,
            from_=150,
            to=1800,
            suffix="ms",
            command=self.sync_settings,
        )

        ttk.Label(settings_panel, text="Tipo de clique", style="Panel.TLabel").grid(
            row=6, column=0, sticky="w", pady=(18, 8)
        )
        modes = ttk.Frame(settings_panel, style="Panel.TFrame")
        modes.grid(row=7, column=0, sticky="ew")
        modes.columnconfigure((0, 1, 2), weight=1)
        for idx, (text, value) in enumerate(
            [("Esquerdo", "left"), ("Direito", "right"), ("Duplo", "double")]
        ):
            ttk.Radiobutton(
                modes,
                text=text,
                value=value,
                variable=self.click_mode_var,
                command=self.sync_settings,
            ).grid(row=0, column=idx, sticky="w", padx=(0, 10))

        ttk.Checkbutton(
            settings_panel,
            text="Mostrar indicador circular no cursor",
            variable=self.feedback_var,
            command=self.sync_settings,
        ).grid(row=8, column=0, sticky="w", pady=(20, 0))

        color_row = ttk.Frame(settings_panel, style="Panel.TFrame")
        color_row.grid(row=9, column=0, sticky="ew", pady=(14, 0))
        color_row.columnconfigure(1, weight=1)
        ttk.Label(color_row, text="Cor do indicador", style="Panel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        color_picker = ttk.Combobox(
            color_row,
            textvariable=self.color_var,
            values=list(INDICATOR_COLORS.keys()),
            state="readonly",
            width=14,
        )
        color_picker.grid(row=0, column=1, sticky="e")
        color_picker.bind("<<ComboboxSelected>>", lambda _event: self.sync_settings())

        ttk.Button(
            settings_panel,
            text="Testar indicador",
            command=self.preview_ring,
        ).grid(row=10, column=0, sticky="w", pady=(14, 0))
        ttk.Label(settings_panel, textvariable=self.ring_test_var, style="Panel.TLabel").grid(
            row=11, column=0, sticky="w", pady=(8, 0)
        )

        footer = ttk.Label(
            outer,
            text="Dica: F8 pausa ou ativa sem precisar voltar ao painel.",
            style="Subtitle.TLabel",
        )
        footer.pack(anchor="w", pady=(14, 0))

    def add_slider(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.IntVar,
        from_: int,
        to: int,
        suffix: str,
        command,
    ) -> None:
        header = ttk.Frame(parent, style="Panel.TFrame")
        header.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=label, style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        value_label = ttk.Label(header, text="", style="Panel.TLabel")
        value_label.grid(row=0, column=1, sticky="e")

        def update_label(*_args) -> None:
            value_label.configure(text=f"{variable.get()} {suffix}")

        variable.trace_add("write", update_label)
        update_label()
        ttk.Scale(
            parent,
            from_=from_,
            to=to,
            variable=variable,
            orient="horizontal",
            command=lambda _value: command(),
        ).grid(row=row + 1, column=0, sticky="ew", pady=(0, 8))

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
            else "Ative quando estiver pronto. F8 alterna rapido."
        )
        self.toggle_button.configure(text="Pausar" if enabled else "Ativar")
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
