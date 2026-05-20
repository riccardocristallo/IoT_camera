# 🎥 IoT Behavioral Analysis System

Real-time behavioral analysis system for indoor environments such as classrooms, laboratories, and meeting rooms.  
It captures the video stream from an IP camera via RTSP and automatically detects:
- **Phone usage** by people in the frame
- **Attention level** estimated through body pose and face orientation

***

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         IP Camera (RTSP)                                │
│                    TAPO C225 → rtsp://…/stream2                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ continuous H.264 frames
                               ▼
                      ┌─────────────────┐
                      │   RTSPReceiver  │  Dedicated thread, circular buffer (2 frames)
                      └────────┬────────┘
                               │ 
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
  ┌────────────────────────┐     ┌──────────────────────────────┐
  │  Processor             │     │  AttentionProcessor          │
  │  (Phone Detection)     │     │  (Attention Detection)       │
  │                        │     │                              │
  │  MediaPipe             │     │  YOLOv8n-pose                │
  │  EfficientDet-Lite2    │     │  → body keypoints            │
  │  → person + cell phone │     │                              │
  │  → overlap check       │     │  MediaPipe FaceLandmarker    │
  │  → annotated frame     │     │  → head pitch (solvePnP)     │
  └────────────┬───────────┘     └──────────────┬───────────────┘
               │                                │
               └──────────────┬─────────────────┘
                              │ annotated frame
                              ▼
                    ┌──────────────────┐
                    │  Display / Main  │  OpenCV imshow + session log
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   ControlPanel   │  Tkinter – parameter panel
                    └──────────────────┘
```

### Main components

| File | Role |
|------|------|
| `main.py` | Entry point: thread orchestration and main OpenCV loop |
| `config.py` | Loads `.env` and centralizes all parameters |
| `rtsp/rtsp_receiver.py` | Receives the RTSP stream in a separate thread |
| `phone_detection/processor.py` | Detects people and phones using MediaPipe EfficientDet-Lite2 |
| `phone_detection/display.py` | OpenCV overlay with phone detection statistics |
| `attention_detection/attention_processor.py` | Attention estimation: YOLOv8 pose + face pitch using FaceLandmarker |
| `attention_detection/attention_summary_popup.py` | Tkinter popup with session chart and KPIs |
| `utils/control_panel.py` | Tkinter control panel |

***

## ⚙️ Operating modes

### 📱 Phone Detection default
Uses **MediaPipe EfficientDet-Lite2** in live stream mode.  
For each frame, it detects `person` and `cell phone`, then checks bounding box overlap to associate a phone with a specific person.

### 👁 Attention Detection
Uses **YOLOv8n-pose** to detect people and estimate body keypoints.  
From the face region, it extracts a crop and passes it to **MediaPipe FaceLandmarker** to calculate the head _pitch_ using `solvePnP`.  
The pitch is compared against configurable thresholds (`DOWN_THRESHOLD`, `UP_THRESHOLD`) to determine whether the person is attentive or distracted.

Two sub-modes:
- **Lecture** (`MODE_DOWN_DISTRACTED`): distracted if looking down (head lowered → phone/book)
- **Practice session** (`MODE_UP_DISTRACTED`): distracted if looking up (not monitoring the screen)

***

## 🚀 Quick start

### 1. Requirements

- Python **3.10 – 3.12**
- Operating system: Windows, macOS, or Linux
- IP camera with an RTSP stream accessible on the local network, for example TAPO C225

### 2. Installation

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# or:
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. `.env` configuration

```bash
cp .env.example .env
```

Open `.env` with a text editor and change at least:

```dotenv
# Your camera URL
RTSP_URL=rtsp://USER:PASSWORD@CAMERA_IP:554/stream2
```

All other parameters have working default values — change them only if necessary.

### 4. Run

```bash
python main.py
```

On the first run, the AI models are downloaded automatically, approximately 10–30 MB in total, and saved in the current directory.

***

## 🎮 Runtime controls

| Key | Action |
|-----|--------|
| `SPACE` | Toggle between Phone Detection and Attention Detection |
| `M` | Change attention criterion: lecture ↔ practice session |
| `P` | Reopen / bring the control panel to the foreground |
| `Q` | Exit the application |

The **control panel** Tkinter window allows you to adjust the confidence threshold with a slider and change the mode using radio buttons.

***

## 🗂 `.env` file management

The `.env` file in the project root is automatically read by `config.py` through the `python-dotenv` library.

### Available parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `RTSP_URL` | `rtsp://localhost:8554/video` | Camera RTSP stream URL |
| `WINDOW_NAME` | `IoT Camera - Phone Detection` | OpenCV window title |
| `PHONE_MODEL_PATH` | `efficientdet_lite2.tflite` | Local path of the EfficientDet model |
| `PHONE_MODEL_URL` | *(GCS URL)* | Download URL for the EfficientDet model |
| `PHONE_CONF_THRESHOLD` | `0.35` | Initial phone detector confidence threshold (0.01–0.95) |
| `YOLO_MODEL_PATH` | `yolov8n-pose.pt` | Local path of the YOLOv8 model |
| `YOLO_MODEL_URL` | *(GitHub URL)* | Download URL for the YOLOv8 model |
| `YOLO_CONF_THRESHOLD` | `0.45` | Initial YOLO confidence threshold (0.01–0.95) |
| `FACE_LANDMARKER_PATH` | `face_landmarker.task` | Local path of the FaceLandmarker model |
| `FACE_LANDMARKER_URL` | *(GCS URL)* | Download URL for the FaceLandmarker model |
| `DOWN_THRESHOLD` | `-18.0` | Pitch angle in degrees below which the head is considered lowered |
| `UP_THRESHOLD` | `12.0` | Pitch angle in degrees above which the head is considered raised |
| `MIN_PROCESS_INTERVAL` | `0.12` | Minimum interval in seconds between two attention inferences |

***

## 📦 Dependencies (`requirements.txt`)

| Package | Minimum version | Usage |
|---------|-----------------|-------|
| `opencv-python` | 4.9.0 | Video capture, rendering, solvePnP |
| `mediapipe` | 0.10.14 | EfficientDet-Lite2 for phone detection + FaceLandmarker for attention |
| `ultralytics` | 8.4.0 | YOLOv8n-pose for body keypoints |
| `numpy` | 1.26.0 | Array processing and camera matrices |
| `python-dotenv` | 1.0.0 | Reading the `.env` file |

`tkinter` is included in the Python standard library. No separate installation is required on Windows/macOS; on Linux: `sudo apt install python3-tk`.

***

## 🏗 Project structure

```
iot-behavioral-analysis/
├── main.py                          # Entry point
├── config.py                        # .env loading and constants
├── .env                             # 🔒 Local configuration (not committed to git)
├── .env.example                     # Public template without secrets
├── .gitignore
├── requirements.txt
│
├── rtsp/
│   └── rtsp_receiver.py             # RTSP stream receiver
│
├── phone_detection/
│   ├── processor.py                 # People + phone detection
│   └── display.py                   # OpenCV overlay
│
├── attention_detection/
│   ├── attention_processor.py       # Attention estimation (YOLO + FaceLandmarker)
│   └── attention_summary_popup.py   # Session summary popup
│
└── utils/
    └── control_panel.py             # Tkinter control panel
```

***

## 🔧 Reference hardware

| Component | Model |
|-----------|-------|
| IP Camera | TP-Link TAPO C225 |
| Router | ZyXEL WAP3205 V2 (N300) |
| Computer | Any PC capable of running real-time inference. Recommended: quad-core CPU, 8 GB RAM |

***

## 📄 License

Academic project — educational use.