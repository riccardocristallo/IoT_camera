from ultralytics import YOLO
import cv2
import threading
import time


class Processor:
    def __init__(self, model_path="yolo11n.pt"):
        self.model = YOLO(model_path)
        self._last_result = (None, 0, 0)
        self._lock = threading.Lock()
        self._running = True
        print(f"[Processor] Modello caricato: {model_path}")

    def start(self, get_frame_fn):
        def _infer():
            TARGET_FPS = 10
            frame_interval = 1.0 / TARGET_FPS
            while self._running:
                t0 = time.time()
                frame = get_frame_fn()
                if frame is None:
                    time.sleep(0.01)
                    continue
                result = self._run(frame)
                with self._lock:
                    self._last_result = result
                elapsed = time.time() - t0
                time.sleep(max(0, frame_interval - elapsed))

        self._thread = threading.Thread(target=_infer, daemon=True)
        self._thread.start()

    def get_result(self):
        with self._lock:
            return self._last_result

    def stop(self):
        self._running = False

    def _boxes_overlap(self, box1, box2, threshold=0.3):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area_phone = (box2[2] - box2[0]) * (box2[3] - box2[1])
        if area_phone == 0:
            return False
        return (intersection / area_phone) >= threshold

    def _run(self, frame):
        h_orig, w_orig = frame.shape[:2]
        # Ridimensiona prima dell'inferenza
        small = cv2.resize(frame, (640, 360))

        # DOPO (abbassa la soglia di confidenza per il telefono)
        results = self.model(small, verbose=False, classes=[0, 67], imgsz=320, conf=0.15)

        scale_x = w_orig / 640
        scale_y = h_orig / 360

        persons = []
        phones_global = []

        for box in results[0].boxes:
            cls = int(box.cls[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            # Scala le coordinate al frame originale
            coords = [x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]
            conf = float(box.conf[0])
            if cls == 0:
                persons.append((coords, conf))
            elif cls == 67:
                phones_global.append(coords)

        # Associa ogni persona al telefono vicino
        persons_with_phone = []
        for (person_box, conf) in persons:
            has_phone = any(
                self._boxes_overlap(person_box, pb) for pb in phones_global
            )
            persons_with_phone.append((person_box, conf, has_phone))

        # Disegna i risultati sul frame originale
        annotated = frame.copy()

        # Telefoni in blu
        for (px1, py1, px2, py2) in phones_global:
            cv2.rectangle(annotated,
                          (int(px1), int(py1)), (int(px2), int(py2)),
                          (255, 150, 0), 2)
            cv2.putText(annotated, "phone", (int(px1), int(py1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 150, 0), 2)

        # Persone: ROSSO con telefono, VERDE senza
        num_with_phone = 0
        for (box, conf, has_phone) in persons_with_phone:
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            if has_phone:
                color = (0, 0, 255)
                label = f"PHONE! {conf:.0%}"
                num_with_phone += 1
            else:
                color = (0, 255, 0)
                label = f"Person {conf:.0%}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return annotated, len(persons_with_phone), num_with_phone