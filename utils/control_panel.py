import tkinter as tk
from tkinter import ttk

class ControlPanel:
    _PANEL_W = 480
    _PANEL_H = 460

    def __init__(self, display, attention_processor_cls, on_mode_change,
                 on_phone_conf_change, on_attention_mode_change):
        self.display = display
        self.attention_processor_cls = attention_processor_cls
        self.on_mode_change = on_mode_change
        self.on_phone_conf_change = on_phone_conf_change
        self.on_attention_mode_change = on_attention_mode_change

        self._current_mode = "phone"

        # --- window BEFORE any tk.Variable ---
        self.root = tk.Tk()
        self.root.title("IoT Camera Controls")
        self.root.geometry(f"{self._PANEL_W}x{self._PANEL_H}+60+60")
        self.root.resizable(False, True)
        self.root.minsize(self._PANEL_W, 280)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- state variables (AFTER tk.Tk()) ---
        self.menu_status_var = tk.StringVar(master=self.root, value="Current mode: PHONE DETECTION")
        self.mode_var = tk.StringVar(master=self.root, value="phone")
        self.phone_conf_var = tk.IntVar(master=self.root, value=display.get_conf_value())
        self.attention_mode_var = tk.StringVar(master=self.root, value=attention_processor_cls.MODE_DOWN_DISTRACTED)

        self._build()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build(self):
        self._canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, padx=14, pady=12)
        self._inner_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

        self._populate()

    def _on_inner_configure(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._inner_id, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-event.delta / 120), "units")

    # ── Widget population ─────────────────────────────────────────────────────
    def _populate(self):
        f = self._inner

        tk.Label(f, text="Control Panel", font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(f, textvariable=self.menu_status_var, font=("Arial", 10),
                 fg="#0055aa").pack(anchor="w", pady=(2, 10))

        # Processing mode
        fm = tk.LabelFrame(f, text="Processing mode", padx=10, pady=8)
        fm.pack(fill="x", pady=(0, 10))
        tk.Radiobutton(fm, text="Phone detection", variable=self.mode_var, value="phone",
                       command=self._on_mode_radio).pack(anchor="w")
        tk.Radiobutton(fm, text="Attention", variable=self.mode_var, value="attention",
                       command=self._on_mode_radio).pack(anchor="w")

        # Confidence
        fc = tk.LabelFrame(f, text="Detector confidence", padx=10, pady=8)
        fc.pack(fill="x", pady=(0, 10))
        tk.Label(fc, text="Confidence threshold (%):", font=("Arial", 9)).pack(anchor="w")
        tk.Scale(fc, from_=1, to=95, orient="horizontal",
                 variable=self.phone_conf_var, length=400,
                 command=lambda v: self.on_phone_conf_change(int(float(v)))).pack(anchor="w")
        tk.Label(fc,
                 text="Applied to both the phone detector and person detection in attention mode.",
                 font=("Arial", 8), fg="#555555", wraplength=400, justify="left").pack(anchor="w", pady=(2, 0))

        # Attention criterion — built but NOT packed immediately
        self._fa = tk.LabelFrame(f, text="Attention criterion [key M]", padx=10, pady=8)
        tk.Radiobutton(self._fa,
                       text="Lecture: distracted if looking down",
                       variable=self.attention_mode_var,
                       value=self.attention_processor_cls.MODE_DOWN_DISTRACTED,
                       command=lambda: self.on_attention_mode_change(self.attention_mode_var.get()),
                       wraplength=380, justify="left").pack(anchor="w", pady=2)
        tk.Radiobutton(self._fa,
                       text="Exercise: distracted if looking up",
                       variable=self.attention_mode_var,
                       value=self.attention_processor_cls.MODE_UP_DISTRACTED,
                       command=lambda: self.on_attention_mode_change(self.attention_mode_var.get()),
                       wraplength=380, justify="left").pack(anchor="w", pady=2)
        tk.Label(self._fa,
                 text="The M key on the video window quickly toggles between the two modes.",
                 font=("Arial", 8), fg="#555555", wraplength=380, justify="left").pack(anchor="w", pady=(4, 0))

        # Keyboard shortcuts — always visible, always at the bottom
        self._fk = tk.LabelFrame(f, text="Keyboard shortcuts (video window active)", padx=10, pady=6)
        self._fk.pack(fill="x", pady=(0, 6))
        shortcuts = [
            ("SPACE", "Toggle mode: phone <-> attention"),
            ("M",     "Toggle criterion: lecture <-> exercise (attention mode only)"),
            ("P",     "Reopen / bring this panel to the front"),
            ("Q",     "Quit the application"),
        ]
        for key, desc in shortcuts:
            row = tk.Frame(self._fk)
            row.pack(anchor="w", pady=1)
            tk.Label(row, text=f"[{key}]", font=("Courier", 9, "bold"), width=9,
                     anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=("Arial", 9),
                     wraplength=340, justify="left").pack(side="left")

        self.update_attention_section_visibility("phone")

    # ── Attention section visibility ──────────────────────────────────────────
    def update_attention_section_visibility(self, mode: str):
        self._current_mode = mode
        if mode == "attention":
            self._fa.pack(fill="x", pady=(0, 10), before=self._fk)
        else:
            self._fa.pack_forget()
        self._inner.update_idletasks()
        self._on_inner_configure()

    # ── Window close handling ─────────────────────────────────────────────────
    def _on_close(self):
        self.root.withdraw()

    def show(self):
        """Bring the panel to the foreground (key P)."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_mode_radio(self):
        self.on_mode_change(self.mode_var.get())

    # ── Public API ────────────────────────────────────────────────────────────
    def update(self):
        self.root.update_idletasks()
        self.root.update()

    def destroy(self):
        self.root.destroy()

    def set_status(self, text: str):
        self.menu_status_var.set(text)

    def set_mode(self, mode: str):
        self.mode_var.set(mode)

    def get_mode(self) -> str:
        return self.mode_var.get()

    def set_phone_conf(self, conf_pct: int):
        self.phone_conf_var.set(conf_pct)

    def get_phone_conf(self) -> int:
        return self.phone_conf_var.get()

    def set_attention_mode(self, mode: str):
        self.attention_mode_var.set(mode)

    def get_attention_mode(self) -> str:
        return self.attention_mode_var.get()
