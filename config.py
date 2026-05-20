import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

def _get(key: str, default: str) -> str:
    return os.environ.get(key, default)

def _get_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default

# ── Stream ────────────────────────────────────────────────────────────────────
RTSP_URL: str = _get("RTSP_URL", "rtsp://localhost:8554/video")
WINDOW_NAME: str = _get("WINDOW_NAME", "IoT Camera - Phone Detection")

# ── Phone Detection ───────────────────────────────────────────────────────────
PHONE_MODEL_PATH: str = _get("PHONE_MODEL_PATH", "efficientdet_lite2.tflite")
PHONE_MODEL_URL: str = _get("PHONE_MODEL_URL",
    "https://storage.googleapis.com/mediapipe-models/object_detector/"
    "efficientdet_lite2/float32/1/efficientdet_lite2.tflite")
PHONE_CONF_THRESHOLD: float = _get_float("PHONE_CONF_THRESHOLD", 0.35)

# ── Attention Detection ───────────────────────────────────────────────────────
YOLO_MODEL_PATH: str = _get("YOLO_MODEL_PATH", "yolov8n-pose.pt")
YOLO_MODEL_URL: str = _get("YOLO_MODEL_URL",
    "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n-pose.pt")
YOLO_CONF_THRESHOLD: float = _get_float("YOLO_CONF_THRESHOLD", 0.35)

FACE_LANDMARKER_PATH: str = _get("FACE_LANDMARKER_PATH", "face_landmarker.task")
FACE_LANDMARKER_URL: str = _get("FACE_LANDMARKER_URL",
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task")

# ── Head angle thresholds ─────────────────────────────────────────────────────
DOWN_THRESHOLD: float = _get_float("DOWN_THRESHOLD", -18.0)
UP_THRESHOLD: float = _get_float("UP_THRESHOLD", 12.0)

# ── Performance ───────────────────────────────────────────────────────────────
MIN_PROCESS_INTERVAL: float = _get_float("MIN_PROCESS_INTERVAL", 0.12)
