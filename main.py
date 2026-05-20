import time
import threading
import tkinter as tk
import cv2
import queue

from rtsp.rtsp_receiver import RTSPReceiver
from phone_detection.processor import Processor
from phone_detection.display import Display
from attention_detection.attention_processor import AttentionProcessor
from utils.control_panel import ControlPanel
from attention_detection.attention_summary_popup import show_attention_summary_popup


RTSP_URL = "rtsp://prova1234:prova1234@192.168.1.33:554/stream2"
#RTSP_URL = "rtsp://localhost:8554/video"
WINDOW_NAME = "IoT Camera - Phone Detection"


receiver = RTSPReceiver(RTSP_URL)
processor = Processor()
attention = None
mode = "phone"
display = Display(WINDOW_NAME, processor=processor)
panel = None
running = True


_ui_queue = queue.SimpleQueue()


def show_attention_popup(summary):
    def _show():
        show_attention_summary_popup(panel.root, summary)
    _ui_queue.put(_show)


def sync_panel_from_runtime():
    if panel is None:
        return
    panel.set_phone_conf(display.get_conf_value())
    panel.set_mode(mode)
    if attention is None:
        panel.set_attention_mode(AttentionProcessor.MODE_DOWN_DISTRACTED)
    else:
        panel.set_attention_mode(attention.get_mode())
    panel.update_attention_section_visibility(mode)


def apply_phone_conf(conf_pct):
    """Applica la soglia confidence sia al phone detector sia all'attention processor."""
    val = max(1, min(conf_pct, 95))
    display.set_conf_value(val)
    if attention is not None:
        attention.set_conf_threshold(val / 100.0)


def apply_attention_mode(selected_mode):
    if attention is not None:
        attention.set_mode(selected_mode)


def switch_to_attention():
    global attention, mode
    if mode == "attention":
        return

    print("[Main] Passaggio a modalità ATTENZIONE...")
    processor.stop()
    time.sleep(0.2)

    attention = AttentionProcessor()
    conf_val = panel.get_phone_conf() / 100.0 if panel is not None else 0.45
    attention.set_conf_threshold(conf_val)
    attention.start(receiver.get_frame)
    attention.reset_session()
    attention.set_mode(panel.get_attention_mode() if panel else AttentionProcessor.MODE_DOWN_DISTRACTED)

    mode = "attention"
    sync_panel_from_runtime()
    panel.set_status("Modalità attuale: ATTENZIONE")
    print("[Main] Modalità ATTENZIONE attivata")


def switch_to_phone():
    global processor, attention, mode
    if mode == "phone":
        return

    print("[Main] Passaggio a modalità PHONE DETECTION...")
    summary = attention.get_session_summary() if attention is not None else {
        "avg_attention": 0.0, "checks": 0, "log": []
    }

    if attention is not None:
        attention.stop()
        time.sleep(0.2)
        attention = None

    processor = Processor()
    display.processor = processor
    apply_phone_conf(panel.get_phone_conf())
    processor.start(receiver.get_frame)

    threading.Thread(target=show_attention_popup, args=(summary,), daemon=True).start()

    mode = "phone"
    sync_panel_from_runtime()
    panel.set_status("Modalità attuale: PHONE DETECTION")
    print("[Main] Modalità PHONE DETECTION attivata")


def on_mode_change(selected):
    if selected == "attention":
        switch_to_attention()
    else:
        switch_to_phone()


def toggle_mode():
    """Alterna tra phone e attention (barra spaziatrice)."""
    if mode == "phone":
        switch_to_attention()
    else:
        switch_to_phone()


def toggle_attention_submode():
    """Alterna lezione/esercitazione (tasto M, solo in modalità attention)."""
    if mode != "attention" or attention is None:
        return
    attention.toggle_mode()
    new_mode = attention.get_mode()
    if panel is not None:
        panel.set_attention_mode(new_mode)
    print(f"[Main] Submodalità attenzione → {new_mode}")


def open_panel():
    """Riporta in primo piano il pannello di controllo (tasto P)."""
    if panel is not None:
        panel.show()


receiver.start()
processor.start(receiver.get_frame)
panel = ControlPanel(
    display=display,
    attention_processor_cls=AttentionProcessor,
    on_mode_change=on_mode_change,
    on_phone_conf_change=apply_phone_conf,
    on_attention_mode_change=apply_attention_mode,
)
sync_panel_from_runtime()

cv2.namedWindow(WINDOW_NAME)
print("[Main] In attesa del primo frame... | Q = esci | SPAZIO = cambia modalità | M = lezione/esercitazione | P = apri pannello")

try:
    while running:
        while not _ui_queue.empty():
            fn = _ui_queue.get_nowait()
            fn()
        panel.update()

        frame = receiver.get_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        if mode == "phone":
            annotated, num_persons, num_with_phone = processor.get_result()
            if annotated is None:
                annotated = frame
            display.show(annotated, num_persons, num_with_phone)
        else:
            annotated = attention.get_result() if attention is not None else None
            if annotated is None:
                annotated = frame
            cv2.imshow(WINDOW_NAME, annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            toggle_mode()
        elif key == ord('m') or key == ord('M'):
            toggle_attention_submode()
        elif key == ord('p') or key == ord('P'):
            open_panel()

finally:
    running = False
    receiver.stop()
    try:
        processor.stop()
    except Exception:
        pass
    if attention is not None:
        attention.stop()
    display.close()
    try:
        panel.destroy()
    except Exception:
        pass
