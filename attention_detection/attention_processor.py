import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
import threading
import time
import urllib.request
import os
from ultralytics import YOLO


class AttentionProcessor:
    DOWN_THRESHOLD = -18.0
    UP_THRESHOLD = 12.0
    FACE_CROP_SIZE = 224
    FACE_MARGIN_RATIO = 0.35

    KP_NOSE = 0
    KP_LEFT_EYE = 1
    KP_RIGHT_EYE = 2

    MODE_DOWN_DISTRACTED = "down_distracted"
    MODE_UP_DISTRACTED = "up_distracted"

    def __init__(self):
        self._yolo = YOLO("yolov8n-pose.pt")
        self.model_path = "face_landmarker.task"
        if not os.path.exists(self.model_path):
            print("[AttentionProcessor] Download modello face_landmarker...")
            urllib.request.urlretrieve(
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
                self.model_path
            )

        self._face_3d = np.array([
            [0.0, 0.0, 0.0],
            [0.0, -330.0, -65.0],
            [-225.0, 170.0, -135.0],
            [225.0, 170.0, -135.0],
            [-150.0, -150.0, -125.0],
            [150.0, -150.0, -125.0],
        ], dtype=np.float64)

        self._landmark_ids = [1, 152, 263, 33, 287, 57]
        self._last_result = None
        self._lock = threading.Lock()
        self._running = True
        self._get_frame_fn = None
        self._session_checks = 0
        self._session_attentive = 0
        self.session_log = []
        self._mode = self.MODE_DOWN_DISTRACTED
        self._last_process_time = 0.0
        self._min_process_interval = 0.12
        self._last_annotated = None
        self._frame_count = 0
        print("[AttentionProcessor] Pronto (YOLO + Face Landmarker).")

    def get_mode(self):
        return self._mode

    def set_mode(self, mode):
        if mode in (self.MODE_DOWN_DISTRACTED, self.MODE_UP_DISTRACTED):
            self._mode = mode
            if self._mode == self.MODE_DOWN_DISTRACTED:
                print("[AttentionProcessor] Modalita': LEZIONE (giu' = distratto)")
            else:
                print("[AttentionProcessor] Modalita': ESERCITAZIONE (su = distratto)")

    def _create_landmarker(self):
        base_options = mp_python.BaseOptions(model_asset_path=self.model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.3,
            min_face_presence_confidence=0.3,
            min_tracking_confidence=0.3,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False
        )
        return mp_vision.FaceLandmarker.create_from_options(options)

    def start(self, get_frame_fn):
        self._running = True
        self._get_frame_fn = get_frame_fn
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def get_result(self):
        with self._lock:
            return self._last_result

    def stop(self):
        self._running = False

    def reset_session(self):
        self._session_checks = 0
        self._session_attentive = 0
        self.session_log = []
        print("[AttentionProcessor] Sessione azzerata.")

    def get_session_summary(self):
        if self._session_checks == 0:
            return {"avg_attention": 0.0, "checks": 0, "log": []}
        avg = self._session_attentive / self._session_checks
        return {
            "avg_attention": round(avg, 1),
            "checks": self._session_checks,
            "log": self.session_log.copy()
        }

    def toggle_mode(self):
        if self._mode == self.MODE_DOWN_DISTRACTED:
            self.set_mode(self.MODE_UP_DISTRACTED)
        else:
            self.set_mode(self.MODE_DOWN_DISTRACTED)

    def handle_click(self, x, y):
        return None

    def _loop(self):
        landmarker = self._create_landmarker()

        while self._running:
            frame = self._get_frame_fn()
            if frame is None:
                time.sleep(0.01)
                continue

            now = time.time()
            self._frame_count += 1

            if (now - self._last_process_time) < self._min_process_interval:
                if self._last_annotated is not None:
                    with self._lock:
                        self._last_result = self._last_annotated.copy()
                time.sleep(0.01)
                continue

            self._last_process_time = now

            try:
                annotated = self._run(frame, self._frame_count, landmarker)
                self._last_annotated = annotated.copy()
                with self._lock:
                    self._last_result = annotated
            except Exception as e:
                print(f"[AttentionProcessor] Errore nel thread: {e}")
                fallback = frame.copy()
                self._draw_hud(fallback, 0, 0, 0, fallback.shape[1], fallback.shape[0], self._frame_count)
                self._last_annotated = fallback
                with self._lock:
                    self._last_result = fallback

        landmarker.close()

    def _run(self, frame, frame_count, landmarker):
        img_h, img_w = frame.shape[:2]
        annotated = frame.copy()

        yolo_results = self._yolo.track(
            frame,
            persist=True,
            classes=[0],
            conf=0.45,
            iou=0.5,
            imgsz=320,
            verbose=False
        )

        if not yolo_results or yolo_results[0].boxes is None:
            self._draw_hud(annotated, 0, 0, 0, img_w, img_h, frame_count)
            return annotated

        result = yolo_results[0]
        boxes = result.boxes
        keypoints = result.keypoints

        if keypoints is None or keypoints.data is None:
            self._draw_hud(annotated, 0, 0, 0, img_w, img_h, frame_count)
            return annotated

        kp_data = keypoints.data.cpu().numpy()
        track_ids = boxes.id.int().cpu().tolist() if boxes.id is not None else list(range(len(boxes)))

        num_faces = 0
        num_attentive = 0

        for idx, (track_id, kps) in enumerate(zip(track_ids, kp_data)):
            x1p, y1p, x2p, y2p = map(int, boxes.xyxy[idx].cpu().tolist())
            face_crop, roi_x, roi_y, roi_w, roi_h = self._get_face_crop(
                frame, kps, x1p, y1p, x2p, y2p, img_w, img_h
            )

            if face_crop is None:
                continue

            num_faces += 1
            rgb = np.ascontiguousarray(cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB))
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            lm_result = landmarker.detect(mp_img)

            if not lm_result.face_landmarks:
                cv2.rectangle(annotated, (x1p, y1p), (x2p, y2p), (128, 128, 128), 1)
                cv2.rectangle(annotated, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (128, 128, 128), 1)
                cv2.putText(annotated, f"#{track_id} no-landmarks",
                            (x1p, max(0, y1p - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.40, (128, 128, 128), 1)
                continue

            pitch = self._estimate_pitch(
                lm_result.face_landmarks[0],
                self.FACE_CROP_SIZE,
                self.FACE_CROP_SIZE
            )

            if pitch is None:
                continue

            distracted = self._is_distracted(pitch)
            if distracted:
                color = (0, 0, 255)
                status = f"#{track_id} DISTRATTO ({pitch:.1f})"
            else:
                num_attentive += 1
                color = (0, 255, 0)
                status = f"#{track_id} ATTENTO ({pitch:.1f})"

            cv2.rectangle(annotated, (x1p, y1p), (x2p, y2p), color, 2)
            cv2.rectangle(annotated, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), color, 1)
            cv2.putText(annotated, status, (x1p, max(0, y1p - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

        if num_faces > 0:
            pct = num_attentive / num_faces * 100
            self._session_checks += 1
            self._session_attentive += pct
            self.session_log.append((time.strftime("%H:%M:%S"), round(pct, 1)))
        else:
            pct = 0

        self._draw_hud(annotated, num_faces, num_attentive, pct, img_w, img_h, frame_count)
        return annotated

    def _is_distracted(self, pitch):
        if self._mode == self.MODE_DOWN_DISTRACTED:
            return pitch < self.DOWN_THRESHOLD
        return pitch > self.UP_THRESHOLD

    def _get_mode_label(self):
        if self._mode == self.MODE_DOWN_DISTRACTED:
            return "LEZIONE: distratto se guarda in basso"
        return "ESERCITAZIONE: distratto se guarda in alto"

    def _get_face_crop(self, frame, kps, x1p, y1p, x2p, y2p, img_w, img_h):
        nose_conf = float(kps[self.KP_NOSE, 2])
        leye_conf = float(kps[self.KP_LEFT_EYE, 2])
        reye_conf = float(kps[self.KP_RIGHT_EYE, 2])

        if nose_conf > 0.25:
            cx = int(kps[self.KP_NOSE, 0])
            cy = int(kps[self.KP_NOSE, 1])
            base = max(40, int((y2p - y1p) * self.FACE_MARGIN_RATIO))
        elif leye_conf > 0.25 and reye_conf > 0.25:
            cx = int((kps[self.KP_LEFT_EYE, 0] + kps[self.KP_RIGHT_EYE, 0]) / 2)
            cy = int((kps[self.KP_LEFT_EYE, 1] + kps[self.KP_RIGHT_EYE, 1]) / 2)
            base = max(40, int((y2p - y1p) * self.FACE_MARGIN_RATIO))
        else:
            cx = (x1p + x2p) // 2
            cy = y1p + int((y2p - y1p) * 0.18)
            base = max(40, int((y2p - y1p) * 0.22))

        rx1 = max(0, cx - base)
        ry1 = max(0, cy - base)
        rx2 = min(img_w, cx + base)
        ry2 = min(img_h, cy + base)
        roi_w = rx2 - rx1
        roi_h = ry2 - ry1

        if roi_w < 30 or roi_h < 30:
            return None, rx1, ry1, roi_w, roi_h

        crop = frame[ry1:ry2, rx1:rx2]
        if crop.size == 0:
            return None, rx1, ry1, roi_w, roi_h

        crop = cv2.resize(crop, (self.FACE_CROP_SIZE, self.FACE_CROP_SIZE))
        return crop, rx1, ry1, roi_w, roi_h

    def _estimate_pitch(self, landmarks, img_w, img_h):
        face_2d = np.array([
            [landmarks[i].x * img_w, landmarks[i].y * img_h]
            for i in self._landmark_ids
        ], dtype=np.float64)

        focal = img_w
        cam_matrix = np.array([
            [focal, 0, img_w / 2],
            [0, focal, img_h / 2],
            [0, 0, 1]
        ], dtype=np.float64)

        dist = np.zeros((4, 1), dtype=np.float64)
        success, rot_vec, _ = cv2.solvePnP(
            self._face_3d, face_2d, cam_matrix, dist,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not success:
            return None

        rot_mat, _ = cv2.Rodrigues(rot_vec)
        angles, *_ = cv2.RQDecomp3x3(rot_mat)
        return angles[0] * 360

    def _draw_hud(self, annotated, num_faces, num_attentive, pct, img_w, img_h, frame_count):
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (620, 110), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, annotated, 0.45, 0, annotated)

        cv2.putText(annotated, "MODALITA': ATTENZIONE", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 220, 255), 2)
        cv2.putText(annotated, self._get_mode_label(), (10, 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 220, 120), 1)
        cv2.putText(annotated, f"Attenti ora: {num_attentive}/{num_faces} ({pct:.0f}%)", (10, 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 120), 1)

        summary = self.get_session_summary()
        cv2.putText(annotated,
                    f"Media sessione: {summary['avg_attention']:.1f}% | campioni: {summary['checks']}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1)
