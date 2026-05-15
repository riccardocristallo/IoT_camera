import cv2

TRACKBAR_NAME = "Conf %"
TRACKBAR_MAX  = 95          # valore massimo slider (95 → 0.95)
DEFAULT_CONF  = 35          # valore iniziale slider (35 → 0.35)


class Display:
    def __init__(self, window_name: str = "IoT Camera", processor=None):
        self.window_name = window_name
        self._processor  = processor   # riferimento al Processor per aggiornare la soglia

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        # Crea lo slider nella finestra OpenCV
        cv2.createTrackbar(
            TRACKBAR_NAME,
            self.window_name,
            DEFAULT_CONF,           # valore iniziale
            TRACKBAR_MAX,           # valore massimo
            self._on_trackbar       # callback chiamato ad ogni movimento
        )

    def _on_trackbar(self, value: int):
        """Callback chiamato da OpenCV ogni volta che lo slider si muove."""
        # Impedisce conf=0 (ogni detection sarebbe accettata)
        conf = max(value, 1) / 100.0
        if self._processor is not None:
            self._processor.score_threshold = conf

    def show(self, frame, num_persons: int, num_with_phone: int):
        # Leggi il valore corrente dello slider per mostrarlo nel frame
        try:
            conf_val = cv2.getTrackbarPos(TRACKBAR_NAME, self.window_name)
        except cv2.error:
            conf_val = 25  # valore di default se la finestra non esiste ancora
        #conf_val = cv2.getTrackbarPos(TRACKBAR_NAME, self.window_name)
        conf_pct = max(conf_val, 1)

        cv2.putText(frame,
                    f"Persons: {num_persons}  |  With phone: {num_with_phone}",
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        if num_with_phone > 0:
            cv2.putText(frame, "PHONE DETECTED!", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        # Mostra la soglia attiva in basso a sinistra
        h = frame.shape[0]
        cv2.putText(frame, f"Conf threshold: {conf_pct}%",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        cv2.imshow(self.window_name, frame)

    def should_quit(self) -> bool:
        return cv2.waitKey(1) & 0xFF == ord('q')

    def close(self):
        cv2.destroyAllWindows()
