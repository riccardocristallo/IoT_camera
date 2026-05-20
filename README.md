# 🎥 IoT Behavioral Analysis System

Sistema di analisi comportamentale in tempo reale per ambienti indoor (aule, laboratori, sale riunioni).  
Acquisisce lo stream video da una telecamera IP via RTSP e rileva automaticamente:
- **Utilizzo del telefono** da parte delle persone inquadrate
- **Livello di attenzione** stimato tramite pose corporea e orientamento del volto

***

## 📐 Architettura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Telecamera IP (RTSP)                            │
│                    TAPO C225 → rtsp://…/stream2                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ frame H.264 continuo
                               ▼
                      ┌─────────────────┐
                      │   RTSPReceiver  │  Thread dedicato, buffer circolare (2 frame)
                      └────────┬────────┘
                               │ frame BGR (NumPy)
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
  ┌────────────────────────┐     ┌──────────────────────────────┐
  │  Processor             │     │  AttentionProcessor          │
  │  (Phone Detection)     │     │  (Attention Detection)       │
  │                        │     │                              │
  │  MediaPipe             │     │  YOLOv8n-pose                │
  │  EfficientDet-Lite2    │     │  → keypoints corpo           │
  │  → person + cell phone │     │                              │
  │  → overlap check       │     │  MediaPipe FaceLandmarker    │
  │  → annotated frame     │     │  → pitch testa (solvePnP)    │
  └────────────┬───────────┘     └──────────────┬───────────────┘
               │                                │
               └──────────────┬─────────────────┘
                              │ frame annotato
                              ▼
                    ┌──────────────────┐
                    │  Display / Main  │  OpenCV imshow + log sessione
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   ControlPanel   │  Tkinter – pannello parametri
                    └──────────────────┘
```

### Componenti principali

| File | Ruolo |
|------|-------|
| `main.py` | Entry point: orchestrazione dei thread, loop principale OpenCV |
| `config.py` | Carica `.env` e centralizza tutti i parametri |
| `rtsp/rtsp_receiver.py` | Ricezione stream RTSP in thread separato |
| `phone_detection/processor.py` | Rilevamento persone e telefoni (MediaPipe EfficientDet-Lite2) |
| `phone_detection/display.py` | Overlay OpenCV con statistiche phone detection |
| `attention_detection/attention_processor.py` | Stima attenzione: pose YOLOv8 + pitch volto (FaceLandmarker) |
| `attention_detection/attention_summary_popup.py` | Popup Tkinter con grafico e KPI sessione |
| `utils/control_panel.py` | Pannello di controllo Tkinter |

***

## ⚙️ Modalità operative

### 📱 Phone Detection (default)
Utilizza **MediaPipe EfficientDet-Lite2** in modalità live stream.  
Per ogni frame rileva `person` e `cell phone`, poi verifica la sovrapposizione dei bounding box per associare un telefono a una persona specifica.

### 👁 Attention Detection
Utilizza **YOLOv8n-pose** per individuare le persone e stimare i keypoint del corpo.  
Dalla regione del viso estrae un crop e lo passa a **MediaPipe FaceLandmarker** per calcolare il _pitch_ della testa tramite `solvePnP`.  
Il pitch viene confrontato con le soglie configurabili (`DOWN_THRESHOLD`, `UP_THRESHOLD`) per determinare se la persona è attenta o distratta.

Due sotto-modalità:
- **Lezione** (`MODE_DOWN_DISTRACTED`): distratto se guarda in basso (testa abbassata → telefono/libro)
- **Esercitazione** (`MODE_UP_DISTRACTED`): distratto se guarda in alto (non monitora lo schermo)

***

## 🚀 Avvio rapido

### 1. Prerequisiti

- Python **3.10 – 3.12**
- Sistema operativo: Windows, macOS o Linux
- Telecamera IP con stream RTSP accessibile sulla rete locale (es. TAPO C225)

### 2. Installazione

```bash
# Crea e attiva un ambiente virtuale
python -m venv venv
source venv/bin/activate        # Linux/macOS
# oppure:
venv\Scripts\activate           # Windows

# Installa le dipendenze
pip install -r requirements.txt
```

### 3. Configurazione `.env`

```bash
cp .env.example .env
```

Apri `.env` con un editor di testo e modifica almeno:

```dotenv
# URL della tua telecamera
RTSP_URL=rtsp://UTENTE:PASSWORD@IP_CAMERA:554/stream2
```

Tutti gli altri parametri hanno valori predefiniti funzionanti — modificali solo se necessario.

### 4. Avvio

```bash
python main.py
```

Al primo avvio i modelli AI vengono scaricati automaticamente (≈ 10–30 MB totali) e salvati nella directory corrente.

***

## 🎮 Controlli runtime

| Tasto | Azione |
|-------|--------|
| `SPAZIO` | Alterna tra Phone Detection e Attention Detection |
| `M` | Cambia criterio attenzione (lezione ↔ esercitazione) |
| `P` | Riapri / porta in primo piano il pannello di controllo |
| `Q` | Esci dall'applicazione |

Il **pannello di controllo** (finestra Tkinter) consente di regolare la soglia di confidence con uno slider e di cambiare modalità tramite radio button.

***

## 🗂 Gestione del file `.env`

Il file `.env` nella root del progetto viene letto automaticamente da `config.py` tramite la libreria `python-dotenv`.

### Parametri disponibili

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `RTSP_URL` | `rtsp://localhost:8554/video` | URL stream RTSP della telecamera |
| `WINDOW_NAME` | `IoT Camera - Phone Detection` | Titolo della finestra OpenCV |
| `PHONE_MODEL_PATH` | `efficientdet_lite2.tflite` | Percorso locale del modello EfficientDet |
| `PHONE_MODEL_URL` | *(URL GCS)* | URL di download del modello EfficientDet |
| `PHONE_CONF_THRESHOLD` | `0.35` | Soglia confidence iniziale phone detector (0.01–0.95) |
| `YOLO_MODEL_PATH` | `yolov8n-pose.pt` | Percorso locale del modello YOLOv8 |
| `YOLO_MODEL_URL` | *(URL GitHub)* | URL di download del modello YOLOv8 |
| `YOLO_CONF_THRESHOLD` | `0.45` | Soglia confidence iniziale YOLO (0.01–0.95) |
| `FACE_LANDMARKER_PATH` | `face_landmarker.task` | Percorso locale del modello FaceLandmarker |
| `FACE_LANDMARKER_URL` | *(URL GCS)* | URL di download del modello FaceLandmarker |
| `DOWN_THRESHOLD` | `-18.0` | Angolo pitch (°) sotto cui la testa è considerata abbassata |
| `UP_THRESHOLD` | `12.0` | Angolo pitch (°) sopra cui la testa è considerata alzata |
| `MIN_PROCESS_INTERVAL` | `0.12` | Intervallo minimo (secondi) tra due inferenze attenzione |

***

## 📦 Dipendenze (`requirements.txt`)

| Pacchetto | Versione minima | Utilizzo |
|-----------|-----------------|---------|
| `opencv-python` | 4.9.0 | Acquisizione video, rendering, solvePnP |
| `mediapipe` | 0.10.14 | EfficientDet-Lite2 (phone) + FaceLandmarker (attention) |
| `ultralytics` | 8.4.0 | YOLOv8n-pose (keypoint corporei) |
| `numpy` | 1.26.0 | Elaborazione array, matrici camera |
| `python-dotenv` | 1.0.0 | Lettura file `.env` |

`tkinter` è incluso nella libreria standard di Python (nessuna installazione separata necessaria su Windows/macOS; su Linux: `sudo apt install python3-tk`).

***

## 🏗 Struttura del progetto

```
iot-behavioral-analysis/
├── main.py                          # Entry point
├── config.py                        # Caricamento .env e costanti
├── .env                             # 🔒 Configurazione locale (non in git)
├── .env.example                     # Template pubblico senza segreti
├── .gitignore
├── requirements.txt
│
├── rtsp/
│   └── rtsp_receiver.py             # Ricezione stream RTSP
│
├── phone_detection/
│   ├── processor.py                 # Rilevamento persone + telefoni
│   └── display.py                   # Overlay OpenCV
│
├── attention_detection/
│   ├── attention_processor.py       # Stima attenzione (YOLO + FaceLandmarker)
│   └── attention_summary_popup.py   # Popup riepilogo sessione
│
└── utils/
    └── control_panel.py             # Pannello di controllo Tkinter
```

***

## 🔧 Hardware di riferimento

| Componente | Modello |
|------------|---------|
| Telecamera IP | TP-Link TAPO C225 |
| Router | ZyXEL WAP3205 V2 (N300) |
| Computer | Qualsiasi PC in grado di eseguire inferenza real-time (consigliato: CPU quad-core, 8 GB RAM) |

***

## 📄 Licenza

Progetto accademico — uso educativo.