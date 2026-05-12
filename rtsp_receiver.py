import cv2
import threading
from collections import deque


class RTSPReceiver:
    def __init__(self, url):
        self.url = url
        self.buffer = deque(maxlen=2)
        self.running = False
        self._thread = None

    def start(self):
        self.running = True
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Richiedi risoluzione ridotta direttamente dalla sorgente
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

        if not cap.isOpened():
            raise RuntimeError(f"Impossibile connettersi a: {self.url}")

        def _capture():
            while self.running:
                ret, frame = cap.read()
                if ret:
                    self.buffer.append(frame)
            cap.release()

        self._thread = threading.Thread(target=_capture, daemon=True)
        self._thread.start()
        print(f"[RTSPReceiver] Connesso a {self.url}")

    def get_frame(self):
        return self.buffer[-1] if self.buffer else None

    def stop(self):
        self.running = False
        print("[RTSPReceiver] Fermato.")