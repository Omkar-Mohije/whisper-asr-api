# 🎙️ Whisper ASR Pipeline & Web API

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![faster-whisper](https://img.shields.io/badge/ASR%20Engine-faster--whisper-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready **Automatic Speech Recognition (ASR)** REST API and responsive Web Studio powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2).

Turn audio/video recordings into high-accuracy text transcripts, timestamped subtitle files (**SRT**, **VTT**), structured **JSON**, and **ZIP** bundles with real-time audio playback synchronization and Word Error Rate (**WER**) evaluation.

---

## 📑 Table of Contents

- [Architectural Overview](#-architectural-overview)
- [Verification & Bug Fixes from Original Notebook](#-verification--bug-fixes-from-original-notebook)
- [Key Features](#-key-features)
- [Repository Structure](#-repository-structure)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Local Installation](#local-installation)
  - [Docker Setup](#docker-setup)
- [API Reference](#-api-reference)
  - [Interactive OpenAPI / Swagger UI](#interactive-openapi--swagger-ui)
  - [Endpoints & Examples](#endpoints--examples)
- [Deploying to GitHub](#-deploying-to-github)
- [License](#-license)

---

## 🏛️ Architectural Overview

```
                      +-----------------------------+
                      |   Client / Browser / App    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |       FastAPI Server        |
                      |   (/api/v1 routes & Web UI) |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                                           |
               v                                           v
    +--------------------+                       +--------------------+
    | Audio Preprocessor |                       | Whisper Singleton  |
    | (FFmpeg / 16kHz)   |                       | (faster-whisper)   |
    +----------+---------+                       +----------+---------+
               |                                           |
               +---------------------+---------------------+
                                     |
                                     v
                      +-----------------------------+
                      |      ASR Output Engine      |
                      |  TXT | SRT | VTT | JSON     |
                      |  + WER/CER Evaluation       |
                      +-----------------------------+
```

---

## 🔍 Verification & Bug Fixes from Original Notebook

When analyzing the initial implementation in `standard_whisper_asr_pipeline.ipynb`, several critical production limitations and errors were identified and resolved:

| # | Notebook Limitation / Error | Impact | How It Is Fixed in This Repository |
|---|---|---|---|
| **1** | `float(word.start)` and `float(word.end)` crash on punctuation | `TypeError: float() argument must be a string or a real number, not 'NoneType'` when Whisper encounters non-aligned tokens. | Defensive guards in `asr_engine.py`: verifies `word.start is not None` before casting. |
| **2** | Hardcoded file paths (`OUTPUT_DIR / f"{stem}_16k_mono.wav"`) | Concurrent API requests or identical filenames overwrite each other, causing race conditions and corrupted audio. | Isolated UUID-based temporary file streams (`uuid.uuid4().hex`) with automatic cleanup in `finally:` blocks. |
| **3** | Unhandled crash on silent audio (`raise ValueError("Audio appears to be silent.")`) | Crashes the web server with 500 error if quiet or empty audio is sent. | Gracefully flags `is_silent=True` in `audio_utils.py`, returning a clean empty transcript instantly (RTF = 0) without wasting GPU cycles. |
| **4** | Colab-coupled logic (`google.colab`, `%pip`, `!apt-get`) | Cannot run in standard server, desktop, or container environments. | Decoupled into a clean Python module with standard `requirements.txt`, Dockerfile, and cross-platform fallbacks. |
| **5** | Missing WebVTT (`.vtt`) subtitle format | Web browsers requiring HTML5 `<track>` subtitles cannot use SRT directly. | Implemented RFC-compliant WebVTT generator in `exporters.py` alongside SRT, TXT, JSON, and ZIP. |
| **6** | No Web / API layer (as noted in notebook Section 12) | Notebook was script-only; no client could connect over HTTP. | Built a complete asynchronous FastAPI backend with Swagger docs and a modern Web UI with microphone recording. |

---

## ✨ Key Features

- 🚀 **Blazing Fast Inference**: Uses CTranslate2 under the hood for up to 4x faster execution than vanilla Transformers with lower VRAM consumption.
- 🎯 **State-of-the-Art Accuracy**: Defaults to `large-v3-turbo` with dynamic selection of `medium`, `small`, `base`, or `tiny`.
- 🔇 **Integrated Voice Activity Detection (VAD)**: Automatically detects and strips non-speech silence.
- ⏱️ **Word & Segment Timestamps**: Provides millisecond-precise timing for video subtitles and audio scrubbing.
- 📁 **Multi-Format Export**: One-click download of `.txt`, `.srt`, `.vtt`, `.json`, and packaged `.zip` archives.
- 🎙️ **In-Browser Recording**: Test audio straight from your browser microphone with synced playback highlighting.
- 📊 **Model Benchmarking**: Integrated Word Error Rate (WER) and Character Error Rate (CER) calculation against ground-truth references.

---

## 📂 Repository Structure

```
whisper-asr-api/
├── .env.example             # Template for environment configuration
├── .gitignore               # Git rules ignoring temporary files and caches
├── Dockerfile               # Production container image with FFmpeg
├── docker-compose.yml       # One-command orchestration
├── LICENSE                  # MIT License
├── README.md                # Project documentation
├── requirements.txt         # Pinned Python package dependencies
├── app/
│   ├── __init__.py
│   ├── config.py            # Pydantic environment configuration
│   ├── main.py              # FastAPI application entrypoint & static mounting
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── router.py    # API route registry
│   │       └── endpoints.py # /health, /models, /transcribe, /evaluate
│   ├── core/
│   │   ├── __init__.py
│   │   ├── asr_engine.py    # Thread-safe faster-whisper singleton engine
│   │   ├── audio_utils.py   # Resampling, FFmpeg decoder, silence detection
│   │   ├── evaluation.py    # WER and CER computation via jiwer
│   │   └── exporters.py     # SRT, VTT, TXT, JSON, and ZIP generators
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── asr.py           # Pydantic schemas and serialization models
│   └── static/
│       ├── index.html       # Single-page web studio
│       ├── app.js           # Interactive UI logic & synchronized player
│       └── styles.css       # Clean dark-mode UI stylesheet
└── tests/
    ├── __init__.py
    └── test_api.py          # Automated test suite
```

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+**
2. **FFmpeg** installed and accessible in your system's `PATH`:
   - **Ubuntu/Debian**: `sudo apt update && sudo apt install -y ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: `winget install Gyan.FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html).

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/whisper-asr-api.git
   cd whisper-asr-api
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Open your browser:
   - **Web App**: [http://localhost:8000](http://localhost:8000)
   - **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Docker Setup

To run inside Docker with all FFmpeg and Python dependencies configured:

```bash
docker compose up --build
```

Access the studio at `http://localhost:8000`.

---

## 📡 API Reference

### Interactive OpenAPI / Swagger UI
Browse schemas and test endpoints interactively by navigating to `http://localhost:8000/docs`.

### Endpoints & Examples

#### 1. System Health & Hardware Inspection
```bash
curl -X GET "http://localhost:8000/api/v1/health"
```
**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "model_loaded": true,
  "current_model": "large-v3-turbo",
  "device": "cuda",
  "compute_type": "float16",
  "cuda_available": true,
  "gpu_name": "NVIDIA GeForce RTX 4090"
}
```

#### 2. Transcribe Audio (JSON Output)
```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -F "file=@sample.wav" \
  -F "language=en" \
  -F "word_timestamps=true"
```

#### 3. Transcribe & Download Subtitles Directly (SRT / VTT / ZIP)
```bash
# Download SRT subtitle
curl -X POST "http://localhost:8000/api/v1/transcribe/export" \
  -F "file=@recording.mp3" \
  -F "export_format=srt" \
  -o recording.srt

# Download Complete ZIP (contains TXT, SRT, VTT, JSON)
curl -X POST "http://localhost:8000/api/v1/transcribe/export" \
  -F "file=@recording.mp3" \
  -F "export_format=zip" \
  -o recording_bundle.zip
```

#### 4. Evaluate Accuracy (WER / CER)
```bash
curl -X POST "http://localhost:8000/api/v1/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_text": "the quick brown fox jumps over the lazy dog",
    "hypothesis_text": "the quick brown fox jumped over the lazy dog"
  }'
```

---

## 🐙 Deploying to GitHub

To push this project to your GitHub account:

1. **Initialize Git inside the project directory**:
   ```bash
   cd whisper-asr-api
   git init
   ```

2. **Stage and commit all files**:
   ```bash
   git add .
   git commit -m "feat: initial commit for whisper ASR REST API and web studio"
   ```

3. **Link to your remote GitHub repository**:
   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   ```

4. **Push your code**:
   ```bash
   git push -u origin main
   ```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
