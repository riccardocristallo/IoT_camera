import tkinter as tk


class ControlPanel:
    def __init__(self, display, attention_processor_cls, on_mode_change, on_phone_conf_change, on_attention_mode_change):
        self.display = display
        self.attention_processor_cls = attention_processor_cls
        self.on_mode_change = on_mode_change
        self.on_phone_conf_change = on_phone_conf_change
        self.on_attention_mode_change = on_attention_mode_change

        self.root = tk.Tk()
        self.root.title("Controlli IoT Camera")
        self.root.geometry("520x500+60+60")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.menu_status_var = tk.StringVar(value="Modalità attuale: PHONE DETECTION")
        self.mode_var = tk.StringVar(value="phone")
        self.phone_conf_var = tk.IntVar(value=display.get_conf_value())
        self.attention_mode_var = tk.StringVar(value=attention_processor_cls.MODE_DOWN_DISTRACTED)
        self.summary_enabled_var = tk.BooleanVar(value=True)

        self._build()

    def _build(self):
        main = tk.Frame(self.root, padx=12, pady=12)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Pannello controlli", font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(main, textvariable=self.menu_status_var, font=("Arial", 10)).pack(anchor="w", pady=(4, 10))

        frame_mode = tk.LabelFrame(main, text="Modalità elaborazione", padx=10, pady=8)
        frame_mode.pack(fill="x", pady=(0, 10))
        tk.Radiobutton(frame_mode, text="Phone detection", variable=self.mode_var, value="phone",
                       command=lambda: self.on_mode_change(self.mode_var.get())).pack(anchor="w")
        tk.Radiobutton(frame_mode, text="Attenzione", variable=self.mode_var, value="attention",
                       command=lambda: self.on_mode_change(self.mode_var.get())).pack(anchor="w")

        frame_conf = tk.LabelFrame(main, text="Confidence phone detector", padx=10, pady=8)
        frame_conf.pack(fill="x", pady=(0, 10))
        tk.Label(frame_conf, text="Soglia confidence (%):", font=("Arial", 9)).pack(anchor="w")
        tk.Scale(frame_conf, from_=1, to=95, orient="horizontal", variable=self.phone_conf_var,
                 command=lambda value: self.on_phone_conf_change(int(float(value))), length=430).pack(anchor="w")
        tk.Label(frame_conf,
                 text="La soglia è gestita solo qui: nessuno slider resta sulla finestra video.",
                 font=("Arial", 8), fg="#555555").pack(anchor="w", pady=(2, 0))

        frame_attention = tk.LabelFrame(main, text="Criterio attenzione", padx=10, pady=8)
        frame_attention.pack(fill="x", pady=(0, 10))
        tk.Radiobutton(frame_attention,
                       text="Lezione: distratto se guarda in basso",
                       variable=self.attention_mode_var,
                       value=self.attention_processor_cls.MODE_DOWN_DISTRACTED,
                       command=lambda: self.on_attention_mode_change(self.attention_mode_var.get())).pack(anchor="w")
        tk.Radiobutton(frame_attention,
                       text="Esercitazione: distratto se guarda in alto",
                       variable=self.attention_mode_var,
                       value=self.attention_processor_cls.MODE_UP_DISTRACTED,
                       command=lambda: self.on_attention_mode_change(self.attention_mode_var.get())).pack(anchor="w")

        frame_popup = tk.LabelFrame(main, text="Popup riepilogo phone", padx=10, pady=8)
        frame_popup.pack(fill="x")
        tk.Checkbutton(frame_popup,
                       text="Abilita popup riepilogo periodico",
                       variable=self.summary_enabled_var).pack(anchor="w")

    def update(self):
        self.root.update_idletasks()
        self.root.update()

    def destroy(self):
        self.root.destroy()

    def set_status(self, text):
        self.menu_status_var.set(text)

    def set_mode(self, mode):
        self.mode_var.set(mode)

    def get_mode(self):
        return self.mode_var.get()

    def set_phone_conf(self, conf_pct):
        self.phone_conf_var.set(conf_pct)

    def get_phone_conf(self):
        return self.phone_conf_var.get()

    def set_attention_mode(self, mode):
        self.attention_mode_var.set(mode)

    def get_attention_mode(self):
        return self.attention_mode_var.get()

    def is_summary_enabled(self):
        return bool(self.summary_enabled_var.get())
