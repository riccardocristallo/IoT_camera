import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
import threading
import time
import urllib.request
import os


class AttentionProcessor:
    ATTENTION_PITCH_THRESHOLD = -10

    def __init__(self):
        # Scarica il modello se non presente
        model_path = "face_landmarker.task"
        if not os.path.exists(model_path):
            print("[AttentionProcessor] Download modello face_landmarker...")
            urllib.request.urlretrieve(
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
                model_path
            )

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=10,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.face_landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        self._last_result = None
        self._lock = threading.Lock()
        self._running = True
        self._get_frame_fn = None

        self._session_checks = 0
        self._session_attentive = 0
        self.session_log = []

        self._face_3d = np.array([
            [0.0,    0.0,    0.0   ],
            [0.0,   -330.0, -65.0  ],
            [-225.0, 170.0, -135.0 ],
            [225.0,  170.0, -135.0 ],
            [-150.0,-150.0, -125.0 ],
            [150.0, -150.0, -125.0 ],
        ], dtype=np.float64)

        self._landmark_ids = [1, 152, 263, 33, 287, 57]
        print("[AttentionProcessor] Pronto. Premi SPAZIO per attivare/disattivare.")

    def start(self, get_frame_fn):
        self._get_frame_fn = get_frame_fn
        def _loop():
            while self._running:
                frame = self._get_frame_fn()
                if frame is None:
                    time.sleep(0.03)
                    continue
                annotated = self._run(frame)
                with self._lock:
                    self._last_result = annotated
                time.sleep(0.05)
        self._thread = threading.Thread(target=_loop, daemon=True)
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
            return {"avg_attention": 0, "checks": 0, "log": []}
        avg = self._session_attentive / self._session_checks
        return {
            "avg_attention": round(avg, 1),
            "checks": self._session_checks,
            "log": self.session_log.copy()
        }

    def _estimate_pitch(self, landmarks, img_w, img_h):
        face_2d = np.array([
            [landmarks[i].x * img_w, landmarks[i].y * img_h]
            for i in self._landmark_ids
        ], dtype=np.float64)

        focal = img_w
        cam_matrix = np.array([
            [focal, 0,     img_w / 2],
            [0,     focal, img_h / 2],
            [0,     0,     1        ]
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

    def _run(self, frame):
        img_h, img_w = frame.shape[:2]
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )
        detection_result = self.face_landmarker.detect(mp_image)

        annotated = frame.copy()
        num_faces = 0
        num_attentive = 0

        if detection_result.face_landmarks:
            num_faces = len(detection_result.face_landmarks)

            for face_lm in detection_result.face_landmarks:
                pitch = self._estimate_pitch(face_lm, img_w, img_h)
                if pitch is None:
                    continue

                attentive = pitch < self.ATTENTION_PITCH_THRESHOLD
                if attentive:
                    num_attentive += 1
                    color = (0, 255, 0)
                    status = f"ATTENTO ({pitch:.1f}°)"
                else:
                    color = (0, 0, 255)
                    status = f"DISTRATTO ({pitch:.1f}°)"

                nose = face_lm[1]
                nx, ny = int(nose.x * img_w), int(nose.y * img_h)
                cv2.circle(annotated, (nx, ny), 6, color, -1)

                top = face_lm[10]
                tx, ty = int(top.x * img_w), max(0, int(top.y * img_h) - 15)
                cv2.putText(annotated, status, (tx - 60, ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        pct = (num_attentive / num_faces * 100) if num_faces > 0 else 0
        self._session_checks += 1
        self._session_attentive += pct
        self.session_log.append((time.strftime("%H:%M:%S"), round(pct, 1)))

        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (420, 110), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, annotated, 0.45, 0, annotated)

        cv2.putText(annotated, "MODALITA': ATTENZIONE", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 220, 255), 2)
        cv2.putText(annotated, f"Volti rilevati: {num_faces}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        cv2.putText(annotated, f"Attenti ora:    {num_attentive}/{num_faces}  ({pct:.0f}%)", (10, 78),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 120), 2)

        summary = self.get_session_summary()
        cv2.putText(annotated, f"Media sessione: {summary['avg_attention']:.1f}%  |  campioni: {summary['checks']}", (10, 101),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)
        cv2.putText(annotated, "SPAZIO = torna a Phone Detection",
                    (img_w - 370, img_h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        return annotated