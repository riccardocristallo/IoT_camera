import time
import threading
import tkinter as tk
from tkinter import messagebox
import cv2
from rtsp_receiver import RTSPReceiver
from processor import Processor
from display import Display
from attention_processor import AttentionProcessor


RTSP_URL = "rtsp://prova1234:prova1234@192.168.1.33:554/stream2"

SUMMARY_INTERVAL = 30

receiver  = RTSPReceiver(RTSP_URL)
processor = Processor()
attention = AttentionProcessor()
display   = Display("IoT Camera - Phone Detection", processor=processor)

# Modalità attiva: "phone" o "attention"
mode = "phone"

stats = {
    "max_with_phone": 0,
    "max_persons":    0,
    "lock":           threading.Lock()
}


def show_summary_popup(unique_users, max_persons, interval):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Riepilogo attività",
        f"Ultimi {interval} secondi:\n\n"
        f"Persone che hanno usato il telefono: {unique_users}\n"
        f"Massimo persone in scena: {max_persons}"
    )
    root.destroy()


def show_attention_popup(summary):
    root = tk.Tk()
    root.withdraw()
    log_lines = "\n".join(
        [f"  {t}: {p}%" for t, p in summary["log"][-10:]]
    ) or "  Nessun dato"
    messagebox.showinfo(
        "Riepilogo Attenzione",
        f"Sessione attenzione terminata\n\n"
        f"Media attenzione: {summary['avg_attention']:.1f}%\n"
        f"Campioni rilevati: {summary['checks']}\n\n"
        f"Ultimi rilevamenti:\n{log_lines}"
    )
    root.destroy()


def summary_thread_fn():
    while True:
        time.sleep(SUMMARY_INTERVAL)
        with stats["lock"]:
            unique_users = stats["max_with_phone"]
            max_p        = stats["max_persons"]
            stats["max_with_phone"] = 0
            stats["max_persons"]    = 0
        if mode == "phone":
            threading.Thread(
                target=show_summary_popup,
                args=(unique_users, max_p, SUMMARY_INTERVAL),
                daemon=True
            ).start()


receiver.start()
processor.start(receiver.get_frame)
attention.start(receiver.get_frame)
threading.Thread(target=summary_thread_fn, daemon=True).start()

print("[Main] In attesa del primo frame... | SPAZIO = cambia modalità | Q = esci")

try:
    while True:
        frame = receiver.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        if mode == "phone":
            annotated, num_persons, num_with_phone = processor.get_result()
            if annotated is None:
                annotated = frame

            with stats["lock"]:
                if num_with_phone > stats["max_with_phone"]:
                    stats["max_with_phone"] = num_with_phone
                if num_persons > stats["max_persons"]:
                    stats["max_persons"] = num_persons

            display.show(annotated, num_persons, num_with_phone)

        else:  # mode == "attention"
            annotated = attention.get_result()
            if annotated is None:
                annotated = frame
            cv2.imshow("IoT Camera - Phone Detection", annotated)

        # Gestione tasti
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' '):
            if mode == "phone":
                mode = "attention"
                attention.reset_session()
                print("[Main] Modalità ATTENZIONE attivata")
            else:
                summary = attention.get_session_summary()
                threading.Thread(
                    target=show_attention_popup,
                    args=(summary,),
                    daemon=True
                ).start()
                mode = "phone"
                print("[Main] Modalità PHONE DETECTION attivata")

finally:
    receiver.stop()
    processor.stop()
    attention.stop()
    display.close()