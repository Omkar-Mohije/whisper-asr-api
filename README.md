# 🎙️ Whisper ASR Pipeline & Web API

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Omkar-Mohije/whisper-asr-api/blob/main/whisper_colab_server.ipynb)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![faster-whisper](https://img.shields.io/badge/Model-Whisper%20Large--v3--Turbo-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end **Automatic Speech Recognition (ASR)** system powered by **faster-whisper (Large-v3-Turbo)** and **FastAPI**, designed for high-accuracy multilingual transcription (English, Hindi, Hinglish), subtitle generation (SRT, VTT), and word-level alignment.

---

## 🔄 ASR Pipeline Architecture

```text
                  [ Audio / Video Input ]
            (WAV, MP3, M4A, FLAC, OGG, WebM, MP4)
                              │
                              ▼
        ┌──────────────────────────────────────────────┐
        │ 1. Audio Decoding & Normalization (FFmpeg)   │
        │    • Resample to 16,000 Hz                   │
        │    • Downmix to 1-Channel Mono (float32)     │
        │    • Dynamic Range & Energy Validation       │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 2. Voice Activity Detection (Silero VAD)     │
        │    • Strip non-speech background noise       │
        │    • Speech segmentation (min_silence=500ms) │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 3. Whisper Large-v3-Turbo (CTranslate2)      │
        │    • FP16 GPU / INT8 CPU Inference           │
        │    • Beam Search Decoding (beam_size=5)      │
        │    • Auto Language Detection & Probabilities │
        │    • Millisecond Word & Segment Timestamps   │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 4. Output Generation & Exporters             │
        │    • Plain Text (.txt)                       │
        │    • SubRip Subtitles (.srt)                 │
        │    • WebVTT Subtitles (.vtt)                 │
        │    • Full Structured JSON (.json)            │
        │    • Accuracy Benchmarks: WER & CER (jiwer)  │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ 5. Application & Delivery Layer              │
        │    • Interactive Web Studio (Audio Player)   │
        │    • Asynchronous FastAPI REST API (/docs)   │
        │    • Cloud GPU Tunnel (Google Colab)         │
        └──────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Option A: 1-Click Cloud GPU (Google Colab) — Recommended
Run the complete pipeline on a free **NVIDIA T4 GPU (16 GB VRAM)** with an instant public URL via Cloudflare Tunnel (no account required):

1. Click the **[Open in Colab](https://colab.research.google.com/github/Omkar-Mohije/whisper-asr-api/blob/main/whisper_colab_server.ipynb)** badge.
2. Ensure GPU is enabled (**Runtime ➔ Change runtime type ➔ T4 GPU**).
3. Click **Run All**. The notebook will output a clickable `https://xxxx.trycloudflare.com` URL to open the Web Studio and API.

### Option B: Local Execution
```bash
# 1. Clone repository
git clone https://github.com/Omkar-Mohije/whisper-asr-api.git
cd whisper-asr-api

# 2. Install dependencies (requires FFmpeg installed)
pip install --prefer-binary -r requirements.txt

# 3. Start the FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- **Web Studio**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Option C: Docker
```bash
docker compose up --build
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Hardware status, CUDA device, and active model |
| `GET` | `/api/v1/models` | List supported Whisper model sizes |
| `POST` | `/api/v1/transcribe` | Upload media & receive JSON transcript with word timestamps |
| `POST` | `/api/v1/transcribe/export` | Transcribe and directly download `.srt`, `.vtt`, `.txt`, or `.zip` |
| `POST` | `/api/v1/evaluate` | Calculate Word Error Rate (WER) & Character Error Rate (CER) |

---

## 📂 Repository Structure

```
whisper-asr-api/
├── README.md                  # Project documentation & pipeline diagram
├── requirements.txt           # Pinned dependencies
├── Dockerfile                 # Production Docker image with FFmpeg
├── docker-compose.yml         # Container orchestration
├── whisper_colab_server.ipynb # 1-click Colab GPU server with Cloudflare tunnel
├── .env.example               # Environment defaults
├── .gitignore                 # Git ignore rules
├── LICENSE                    # MIT License
├── app/
│   ├── main.py                # FastAPI entrypoint, static assets & CORS
│   ├── config.py              # Settings & hardware auto-detection
│   ├── api/v1/
│   │   ├── router.py          # Route aggregator
│   │   └── endpoints.py       # API endpoints (/transcribe, /evaluate, /health)
│   ├── core/
│   │   ├── asr_engine.py      # Thread-safe faster-whisper inference singleton
│   │   ├── audio_utils.py     # FFmpeg decoding, resampling, silence detection
│   │   ├── exporters.py       # SRT, VTT, TXT, JSON, and ZIP generators
│   │   └── evaluation.py      # WER and CER calculation via jiwer
│   ├── schemas/
│   │   └── asr.py             # Pydantic v2 data models
│   └── static/
│       ├── index.html         # Responsive Web Studio UI
│       ├── styles.css         # Clean presentation stylesheet
│       └── app.js             # Synchronized cue player & sample library
└── tests/
    └── test_api.py            # Unit & exporter test suite
```

---

## 🎓 Academic Attribution

Developed at the **Indian Institute of Information Technology Allahabad (IIITA)** for the Multimedia Data Processing (MDP) Lab curriculum.  
Built on faster-whisper (CTranslate2) and FastAPI. Distributed under the MIT License.
