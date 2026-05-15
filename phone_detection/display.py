import cv2


class Display:
    def __init__(self, window_name: str = "IoT Camera", processor=None):
        self.window_name = window_name
        self._processor = processor
        self._conf_percent = int(round((processor.score_threshold if processor is not None else 0.35) * 100))
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    @property
    def processor(self):
        return self._processor

    @processor.setter
    def processor(self, value):
        self._processor = value
        if self._processor is not None:
            self._conf_percent = int(round(self._processor.score_threshold * 100))

    def set_conf_value(self, value: int):
        value = max(1, min(value, 95))
        self._conf_percent = value
        if self._processor is not None:
            self._processor.score_threshold = value / 100.0

    def get_conf_value(self) -> int:
        return self._conf_percent

    def show(self, frame, num_persons: int, num_with_phone: int):
        cv2.putText(frame,
                    f"Persons: {num_persons} | With phone: {num_with_phone}",
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2)

        if num_with_phone > 0:
            cv2.putText(frame, "PHONE DETECTED!", (10, 48),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

        h = frame.shape[0]
        cv2.putText(frame, f"Conf threshold: {self._conf_percent}%",
                    (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1)

        cv2.imshow(self.window_name, frame)

    def should_quit(self) -> bool:
        return cv2.waitKey(1) & 0xFF == ord('q')

    def close(self):
        cv2.destroyAllWindows()
