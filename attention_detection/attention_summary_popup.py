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

        # ── Student bar chart ─────────────────────────────────────────────────────
    students = summary.get("students", [])

    tk.Label(win, text="Attention by student",
             font=("Arial", 10, "bold"), bg=DARK_BG, fg=TEXT).pack(
        anchor="w", padx=16, pady=(4, 0))

    CANVAS_H = 220
    chart_canvas = tk.Canvas(
        win,
        height=CANVAS_H,
        bg=CARD_BG,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0
    )
    chart_canvas.pack(fill="x", padx=16, pady=(4, 4))

    def draw_student_bars(canvas):
        canvas.delete("all")
        canvas.update_idletasks()

        W = canvas.winfo_width()
        H = canvas.winfo_height()
        if W < 10 or H < 10:
            W, H = 488, CANVAS_H

        PAD_L, PAD_R, PAD_T, PAD_B = 44, 16, 18, 44
        plot_w = W - PAD_L - PAD_R
        plot_h = H - PAD_T - PAD_B

        # Griglia orizzontale
        for pct in (0, 25, 50, 70, 100):
            y = PAD_T + plot_h - int(pct / 100 * plot_h)
            canvas.create_line(
                PAD_L, y, W - PAD_R, y,
                fill="#2d2c2a", width=1, dash=(4, 4)
            )
            canvas.create_text(
                PAD_L - 6, y, text=f"{pct}%",
                anchor="e", font=("Arial", 7), fill=TEXT_MUTED
            )

        # Soglie
        for thresh, color in ((70, GREEN), (40, ORANGE)):
            y = PAD_T + plot_h - int(thresh / 100 * plot_h)
            canvas.create_line(
                PAD_L, y, W - PAD_R, y,
                fill=color, width=1, dash=(6, 3)
            )

        if not students:
            canvas.create_text(
                W // 2, H // 2,
                text="No student data available",
                fill=TEXT_MUTED, font=("Arial", 10)
            )
        else:
            n = len(students)
            gap = 14
            bar_w = max(24, min(64, int((plot_w - gap * (n + 1)) / max(n, 1))))

            total_bars_w = n * bar_w + (n + 1) * gap
            start_x = PAD_L + max(0, (plot_w - total_bars_w) // 2)

            for i, student in enumerate(students):
                name = student.get("name", f"Student {i+1}")
                att = max(0, min(100, float(student.get("attention", 0))))

                x0 = start_x + gap + i * (bar_w + gap)
                x1 = x0 + bar_w
                y1 = PAD_T + plot_h
                y0 = y1 - int(att / 100 * plot_h)

                color = attention_color(att)

                # Barra
                canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=color, outline=""
                )

                # Valore sopra la barra
                canvas.create_text(
                    (x0 + x1) // 2, y0 - 10,
                    text=f"{att:.0f}%",
                    font=("Arial", 8, "bold"),
                    fill=WHITE if att > 15 else TEXT
                )

                # Nome sotto
                short_name = name if len(name) <= 10 else name[:9] + "…"
                canvas.create_text(
                    (x0 + x1) // 2, y1 + 12,
                    text=short_name,
                    anchor="n",
                    font=("Arial", 7),
                    fill=TEXT_MUTED
                )

        # Assi
        canvas.create_line(PAD_L, PAD_T, PAD_L, PAD_T + plot_h,
                           fill=BORDER, width=1)
        canvas.create_line(PAD_L, PAD_T + plot_h, W - PAD_R, PAD_T + plot_h,
                           fill=BORDER, width=1)

    chart_canvas.bind("<Configure>", lambda e: draw_student_bars(chart_canvas))
    win.after(80, lambda: draw_student_bars(chart_canvas))

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
