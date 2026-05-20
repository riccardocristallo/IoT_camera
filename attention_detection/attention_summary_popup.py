import tkinter as tk
from tkinter import ttk
import time

def show_attention_summary_popup(panel_root, summary: dict):
    avg = summary.get("avg_attention", 0.0)
    checks = summary.get("checks", 0)
    log = summary.get("log", [])

    # ── Colors ────────────────────────────────────────────────────────────────
    DARK_BG = "#1c1b19"
    CARD_BG = "#201f1d"
    BORDER  = "#393836"
    TEXT    = "#cdccca"
    TEXT_MUTED = "#797876"
    TEAL    = "#4f98a3"
    GREEN   = "#6daa45"
    ORANGE  = "#fdab43"
    RED     = "#dd6974"
    WHITE   = "#f0efed"

    def attention_color(pct):
        if pct >= 70:
            return GREEN
        if pct >= 40:
            return ORANGE
        return RED

    # ── Window ────────────────────────────────────────────────────────────────
    win = tk.Toplevel(panel_root)
    win.title("Session Summary — Attention")
    win.attributes("-topmost", True)
    win.resizable(True, True)
    win.minsize(520, 460)
    win.configure(bg=DARK_BG)

    # ── Header ────────────────────────────────────────────────────────────────
    header = tk.Frame(win, bg=DARK_BG)
    header.pack(fill="x", padx=16, pady=(14, 4))

    tk.Label(header, text="📊 Attention session summary",
             font=("Arial", 13, "bold"), bg=DARK_BG, fg=WHITE).pack(side="left")

    now_str = time.strftime("%H:%M %d/%m/%Y")
    tk.Label(header, text=now_str, font=("Arial", 9),
             bg=DARK_BG, fg=TEXT_MUTED).pack(side="right", padx=4)

    ttk.Separator(win, orient="horizontal").pack(fill="x", padx=16, pady=(4, 10))

    # ── KPI cards ─────────────────────────────────────────────────────────────
    kpi_frame = tk.Frame(win, bg=DARK_BG)
    kpi_frame.pack(fill="x", padx=16, pady=(0, 10))

    duration_str = "—"
    if len(log) >= 2:
        try:
            from datetime import datetime
            t0 = datetime.strptime(log[0][0],  "%H:%M:%S")
            t1 = datetime.strptime(log[-1][0], "%H:%M:%S")
            secs = max(0, int((t1 - t0).total_seconds()))
            m, s = divmod(secs, 60)
            duration_str = f"{m}m {s:02d}s"
        except Exception:
            pass

    peak = max((p for _, p in log), default=0.0)
    low  = min((p for _, p in log), default=0.0)

    kpis = [
        ("Avg attention",      f"{avg:.1f}%",  attention_color(avg)),
        ("Peak",               f"{peak:.0f}%", GREEN),
        ("Minimum",            f"{low:.0f}%",  attention_color(low)),
        ("Total samples",      str(checks),    TEAL),
        ("Estimated duration", duration_str,   TEXT_MUTED),
    ]

    for col, (label, value, color) in enumerate(kpis):
        card = tk.Frame(kpi_frame, bg=CARD_BG, bd=0, relief="flat",
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=col, padx=4, pady=2, sticky="nsew")
        kpi_frame.columnconfigure(col, weight=1)

        tk.Label(card, text=label, font=("Arial", 8),
                 bg=CARD_BG, fg=TEXT_MUTED).pack(pady=(8, 0))
        tk.Label(card, text=value, font=("Arial", 15, "bold"),
                 bg=CARD_BG, fg=color).pack(pady=(2, 8))

    # ── Average level bar ─────────────────────────────────────────────────────
    bar_frame = tk.Frame(win, bg=DARK_BG)
    bar_frame.pack(fill="x", padx=16, pady=(0, 8))

    tk.Label(bar_frame, text="Average attention level",
             font=("Arial", 9, "bold"), bg=DARK_BG, fg=TEXT).pack(anchor="w")

    bar_bg = tk.Canvas(bar_frame, height=18, bg=BORDER,
                       highlightthickness=0, bd=0)
    bar_bg.pack(fill="x", pady=(4, 2))

    def draw_bar(canvas):
        canvas.update_idletasks()
        w = canvas.winfo_width()
        if w < 2:
            w = 460
        fill_w = max(4, int(w * avg / 100))
        canvas.delete("all")
        canvas.create_rectangle(0, 0, fill_w, 18,
                                 fill=attention_color(avg), outline="")
        canvas.create_text(fill_w // 2, 9, text=f"{avg:.1f}%",
                           fill=WHITE, font=("Arial", 8, "bold"))

    bar_bg.bind("<Configure>", lambda e: draw_bar(bar_bg))
    win.after(50, lambda: draw_bar(bar_bg))

    tk.Label(bar_frame,
             text="  ≥70% Good    40–70% Fair    <40% Low",
             font=("Arial", 8), bg=DARK_BG, fg=TEXT_MUTED).pack(anchor="w")

    # ── Trend chart ───────────────────────────────────────────────────────────
    tk.Label(win, text="Attention threshold trend over time",
             font=("Arial", 10, "bold"), bg=DARK_BG, fg=TEXT).pack(
        anchor="w", padx=16, pady=(4, 0))

    CANVAS_H = 180
    chart_canvas = tk.Canvas(win, height=CANVAS_H, bg=CARD_BG,
                              highlightbackground=BORDER, highlightthickness=1, bd=0)
    chart_canvas.pack(fill="x", padx=16, pady=(4, 4))

    def draw_chart(canvas):
        canvas.delete("all")
        canvas.update_idletasks()
        W = canvas.winfo_width()
        H = canvas.winfo_height()
        if W < 10 or H < 10:
            W, H = 488, CANVAS_H

        PAD_L, PAD_R, PAD_T, PAD_B = 44, 16, 14, 28
        plot_w = W - PAD_L - PAD_R
        plot_h = H - PAD_T - PAD_B

        # Horizontal grid
        for pct in (0, 25, 50, 70, 100):
            y = PAD_T + plot_h - int(pct / 100 * plot_h)
            canvas.create_line(PAD_L, y, W - PAD_R, y,
                               fill="#2d2c2a", width=1, dash=(4, 4))
            canvas.create_text(PAD_L - 4, y, text=f"{pct}%",
                               anchor="e", font=("Arial", 7), fill=TEXT_MUTED)

        # Colored dashed threshold lines
        for thresh, color in ((70, GREEN), (40, ORANGE)):
            y = PAD_T + plot_h - int(thresh / 100 * plot_h)
            canvas.create_line(PAD_L, y, W - PAD_R, y,
                               fill=color, width=1, dash=(6, 3))

        if not log:
            canvas.create_text(W // 2, H // 2,
                               text="No data available",
                               fill=TEXT_MUTED, font=("Arial", 10))
        else:
            n = len(log)
            xs = [PAD_L + int(i / max(n - 1, 1) * plot_w) for i in range(n)]
            ys = [PAD_T + plot_h - int(p / 100 * plot_h) for _, p in log]

            # Filled area
            if n >= 2:
                for i in range(n - 1):
                    base = PAD_T + plot_h
                    canvas.create_polygon(
                        xs[i], ys[i], xs[i+1], ys[i+1],
                        xs[i+1], base, xs[i], base,
                        fill="#2d3f42", outline=""
                    )

            coords = []
            for x, y in zip(xs, ys):
                coords.extend([x, y])
            canvas.create_line(*coords, fill=TEAL, width=2, smooth=True)

            # Threshold-colored dots
            for i, (x, y) in enumerate(zip(xs, ys)):
                r = 3
                canvas.create_oval(x - r, y - r, x + r, y + r,
                                   fill=attention_color(log[i][1]),
                                   outline=CARD_BG, width=1)

            # X-axis labels (max 6)
            step = max(1, n // 6)
            for i in range(0, n, step):
                canvas.create_text(xs[i], H - PAD_B + 10,
                                   text=log[i][0], anchor="n",
                                   font=("Arial", 7), fill=TEXT_MUTED)

        # Axes
        canvas.create_line(PAD_L, PAD_T, PAD_L, PAD_T + plot_h,
                           fill=BORDER, width=1)
        canvas.create_line(PAD_L, PAD_T + plot_h, W - PAD_R, PAD_T + plot_h,
                           fill=BORDER, width=1)

    chart_canvas.bind("<Configure>", lambda e: draw_chart(chart_canvas))
    win.after(80, lambda: draw_chart(chart_canvas))

    # ── Legend ────────────────────────────────────────────────────────────────
    legend = tk.Frame(win, bg=DARK_BG)
    legend.pack(fill="x", padx=16, pady=(0, 6))
    for color, lbl in [(TEAL, "Trend"), (GREEN, "≥70%"), (ORANGE, "40–70%"), (RED, "<40%")]:
        dot_c = tk.Canvas(legend, width=10, height=10, bg=DARK_BG,
                          highlightthickness=0)
        dot_c.create_oval(1, 1, 9, 9, fill=color, outline="")
        dot_c.pack(side="left", padx=(8, 2))
        tk.Label(legend, text=lbl, font=("Arial", 8),
                 bg=DARK_BG, fg=TEXT_MUTED).pack(side="left", padx=(0, 8))

    # ── Footer with Close only ────────────────────────────────────────────────
    ttk.Separator(win, orient="horizontal").pack(fill="x", padx=16, pady=(6, 0))
    btn_row = tk.Frame(win, bg=DARK_BG)
    btn_row.pack(fill="x", padx=16, pady=(8, 14))

    tk.Button(btn_row, text="Close",
              font=("Arial", 9), bg="#393836", fg=TEXT,
              activebackground="#555", activeforeground=WHITE,
              relief="flat", padx=16, pady=4,
              command=win.destroy).pack(side="right")

    # ── Center relative to the panel ──────────────────────────────────────────
    win.update_idletasks()
    pw = panel_root.winfo_width()  or 480
    ph = panel_root.winfo_height() or 520
    px = panel_root.winfo_x()
    py = panel_root.winfo_y()
    ww = win.winfo_reqwidth()
    wh = win.winfo_reqheight()
    win.geometry(f"{max(520,ww)}x{max(460,wh)}+{px+(pw-ww)//2}+{py+(ph-wh)//2}")
