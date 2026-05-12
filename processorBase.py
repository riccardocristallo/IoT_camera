from ultralytics import YOLO
import cv2
import threading

class Processor:
    def __init__(self, model_path="yolo11n.pt"):
        self.model = YOLO(model_path)
        self._last_result = (None, 0, 0)  
        self._lock = threading.Lock()
        self._running = True
        print(f"[Processor] Modello caricato: {model_path}")

    def start(self, get_frame_fn):
        """Avvia il thread di inferenza in background."""
        def _infer():
            while self._running:
                frame = get_frame_fn()
                if frame is None:
                    continue
                result = self._run(frame)
                with self._lock:
                    self._last_result = result

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
        results = self.model(frame, verbose=False, classes=[0, 67], conf=0.10, imgsz=1280)
        boxes = results[0].boxes

        persons = []
        phones = []

        for box in boxes:
            cls = int(box.cls[0])
            coords = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            if cls == 0:
                persons.append((coords, conf))
            elif cls == 67:
                phones.append(coords)

        persons_with_phone = []
        for (person_box, conf) in persons:
            has_phone = any(self._boxes_overlap(person_box, pb) for pb in phones)
            persons_with_phone.append((person_box, conf, has_phone))

        annotated = frame.copy()

        for (px1, py1, px2, py2) in phones:
            cv2.rectangle(annotated, (int(px1), int(py1)), (int(px2), int(py2)), (255, 150, 0), 2)
            cv2.putText(annotated, "phone", (int(px1), int(py1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 150, 0), 2)

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