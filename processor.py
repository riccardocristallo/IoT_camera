import cv2
import threading
import time
import urllib.request
import os

import mediapipe as mp
from mediapipe.tasks.python import vision as mp_vision

MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float32/1/efficientdet_lite2.tflite"
MODEL_PATH = "efficientdet_lite2.tflite"

PERSON_LABEL = "person"
PHONE_LABEL  = "cell phone"


def _download_model_if_needed(path: str, url: str):
    if not os.path.exists(path):
        print(f"[Processor] Download modello MediaPipe da:\n  {url}")
        urllib.request.urlretrieve(url, path)
        print(f"[Processor] Modello salvato in: {path}")
    else:
        print(f"[Processor] Modello già presente: {path}")


class Processor:
    def __init__(self, model_path: str = MODEL_PATH):
        _download_model_if_needed(model_path, MODEL_URL)

        self._last_result    = (None, 0, 0)
        self._lock           = threading.Lock()
        self._running        = True
        self._timestamp      = 0

        self._raw_detections = []
        self._raw_lock       = threading.Lock()

        # Soglia di confidenza modificabile dall'esterno (thread-safe tramite GIL su float)
        self.score_threshold = 0.35

        BaseOptions    = mp.tasks.BaseOptions
        ObjectDetector = mp_vision.ObjectDetector
        ObjDetOptions  = mp_vision.ObjectDetectorOptions
        RunningMode    = mp_vision.RunningMode

        options = ObjDetOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.LIVE_STREAM,
            max_results=20,
            score_threshold=0.01,   # filtro minimo: il filtraggio reale avviene in _process()
            result_callback=self._on_result,
        )
        self._detector = ObjectDetector.create_from_options(options)
        print(f"[Processor] MediaPipe ObjectDetector caricato: {model_path}")

    # ------------------------------------------------------------------ #
    def _on_result(self, result, output_image, timestamp_ms: int):
        with self._raw_lock:
            self._raw_detections = result.detections

    # ------------------------------------------------------------------ #
    def start(self, get_frame_fn):
        def _infer():
            while self._running:
                frame = get_frame_fn()
                if frame is None:
                    time.sleep(0.005)
                    continue

                rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                self._timestamp += 1
                self._detector.detect_async(mp_image, self._timestamp)

                with self._raw_lock:
                    detections = list(self._raw_detections)

                # Leggi la soglia corrente (impostata dallo slider)
                threshold = self.score_threshold

                annotated_frame, num_persons, num_with_phone = self._process(
                    frame, detections, threshold
                )

                with self._lock:
                    self._last_result = (annotated_frame, num_persons, num_with_phone)

        self._thread = threading.Thread(target=_infer, daemon=True)
        self._thread.start()

    def get_result(self):
        with self._lock:
            return self._last_result

    def stop(self):
        self._running = False
        self._detector.close()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _det_to_xyxy(det, w, h):
        bb = det.bounding_box
        x1 = max(0, int(bb.origin_x))
        y1 = max(0, int(bb.origin_y))
        x2 = min(w, int(bb.origin_x + bb.width))
        y2 = min(h, int(bb.origin_y + bb.height))
        return x1, y1, x2, y2

    @staticmethod
    def _boxes_overlap(box1, box2, threshold=0.3):
        ix1 = max(box1[0], box2[0])
        iy1 = max(box1[1], box2[1])
        ix2 = min(box1[2], box2[2])
        iy2 = min(box1[3], box2[3])
        intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        if area2 == 0:
            return False
        return (intersection / area2) >= threshold

    def _process(self, frame, detections, threshold: float):
        h, w = frame.shape[:2]

        persons = []
        phones  = []

        for det in detections:
            if not det.categories:
                continue
            cat   = det.categories[0]
            # Applica la soglia dinamica qui
            if cat.score < threshold:
                continue
            label = cat.category_name.lower()
            conf  = cat.score
            box   = self._det_to_xyxy(det, w, h)

            if label == PERSON_LABEL:
                persons.append((*box, conf))
            elif label == PHONE_LABEL:
                phones.append(box)

        persons_with_phone = []
        for (x1, y1, x2, y2, conf) in persons:
            has_phone = any(
                self._boxes_overlap((x1, y1, x2, y2), ph) for ph in phones
            )
            persons_with_phone.append((x1, y1, x2, y2, conf, has_phone))

        annotated = frame.copy()

        for (px1, py1, px2, py2) in phones:
            cv2.rectangle(annotated, (px1, py1), (px2, py2), (255, 150, 0), 2)
            cv2.putText(annotated, "phone", (px1, max(py1 - 5, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 150, 0), 2)

        num_with_phone = 0
        for (x1, y1, x2, y2, conf, has_phone) in persons_with_phone:
            if has_phone:
                color     = (0, 0, 255)
                label_txt = f"PHONE! {conf:.0%}"
                num_with_phone += 1
            else:
                color     = (0, 255, 0)
                label_txt = f"Person {conf:.0%}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            (tw, th), _ = cv2.getTextSize(label_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 6, y1), color, -1)
            cv2.putText(annotated, label_txt, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return annotated, len(persons_with_phone), num_with_phone
