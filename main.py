import time
import threading
import tkinter as tk
from tkinter import messagebox
from rtsp_receiver import RTSPReceiver
from processor import Processor
from display import Display

RTSP_URL = "rtsp://prova1234:prova1234@192.168.1.33:554/stream2"
# RTSP_URL = "rtsp://rtsp-server:8554/videoTelefoni"

# Modifica qui l'intervallo del pop-up (in secondi)
SUMMARY_INTERVAL = 30

receiver = RTSPReceiver(RTSP_URL)
processor = Processor("yolo11s.pt")
display = Display("IoT Camera - Phone Detection")

stats = {
    "max_with_phone": 0,  
    "max_persons": 0,
    "lock": threading.Lock()
}

def show_summary_popup(unique_users, max_persons, interval):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "📊 Riepilogo attività",
        f"Ultimi {interval} secondi:\n\n"
        f"📱 Persone che hanno usato il telefono: {unique_users}\n"
        f"👥 Massimo persone in scena: {max_persons}"
    )
    root.destroy()

def summary_thread_fn():
    while True:
        time.sleep(SUMMARY_INTERVAL)
        with stats["lock"]:
            unique_users = stats["max_with_phone"]
            max_p = stats["max_persons"]
            # Reset per il prossimo intervallo
            stats["max_with_phone"] = 0
            stats["max_persons"] = 0
        threading.Thread(
            target=show_summary_popup,
            args=(unique_users, max_p, SUMMARY_INTERVAL),
            daemon=True
        ).start()

receiver.start()
processor.start(receiver.get_frame)
threading.Thread(target=summary_thread_fn, daemon=True).start()

print("[Main] In attesa del primo frame...")

try:
    while True:
        frame = receiver.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        annotated, num_persons, num_with_phone = processor.get_result()
        if annotated is None:
            annotated = frame

        with stats["lock"]:
            if num_with_phone > stats["max_with_phone"]:
                stats["max_with_phone"] = num_with_phone
            if num_persons > stats["max_persons"]:
                stats["max_persons"] = num_persons

        display.show(annotated, num_persons, num_with_phone)

        if display.should_quit():
            break
finally:
    receiver.stop()
    processor.stop()
    display.close()