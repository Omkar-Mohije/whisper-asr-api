# 🎙️ Whisper ASR

**Every Indian has struggled to transcribe a lecture or official audio. Whisper ASR does it in seconds, in your language.**

Whisper ASR is an intelligent voice-first speech recognition assistant that transcribes college lectures, government announcements, and voice notes into clean text, timestamped subtitles (**SRT**, **VTT**), and translated English notes.

**Live demo:** [https://whisper-asr-api.vercel.app](https://whisper-asr-api.vercel.app)  
*(Or tap the 1-click Colab button below for free GPU inference)*

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Omkar-Mohije/whisper-asr-api/blob/main/whisper_colab_server.ipynb)
[![FastAPI](https://img.shields.io/badge/API-FastAPI%20%2B%20GPU-009688.svg)](https://fastapi.tiangolo.com/)
[![Whisper Model](https://img.shields.io/badge/ASR-Whisper%20Large--v3--Turbo-orange.svg)](https://github.com/openai/whisper)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 The Problem

College lectures, seminar presentations, court notices, and official announcements across India are rarely in plain monolingual English. They heavily feature **code-switching (Hinglish)**, regional phrasing (Hindi, Marathi, etc.), noisy classroom acoustics, and fast-paced speech. 

Standard speech-to-text models either fail on Hinglish code-switching or lose synchronization. Students and researchers end up spending hours manually scrubbing audio to transcribe lectures and generate study notes or video subtitles.

---

## 💡 How It Works

1. **Upload or Record**: Upload any audio/video file (WAV, MP3, M4A, FLAC, MP4) or record your voice live from the browser microphone. Or click any of the built-in sample recordings.
2. **Recognize**: Uses **Whisper Large-v3-Turbo** (OpenAI / faster-whisper) with Voice Activity Detection (VAD) to filter silence, align token timestamps, and detect spoken languages automatically.
3. **Interactive Sync**: An interactive audio player synchronizes subtitle cue cards in real time as the audio plays. Clicking any subtitle timestamp seeks the audio to that exact second.
4. **Export**: One-click download of SubRip (**SRT** for VLC/YouTube), WebVTT (**VTT** for HTML5 players), plain text (**TXT**), and structured **JSON**.
5. **Evaluate (WER / CER)**: Built-in benchmark tool comparing Whisper's hypothesis with verified ground-truth reference transcripts to calculate Word Error Rate and Character Error Rate.

---

## 🚀 Live Vercel Deployment (1-Minute Setup)

You can deploy your own live `https://<your-project>.vercel.app` link in 60 seconds:

1. Go to **[vercel.com](https://vercel.com)** and sign in with your GitHub account.
2. Click **"Add New..."** ➔ **"Project"**.
3. Select this repository: `Omkar-Mohije/whisper-asr-api`.
4. *(Optional)* In **Environment Variables**, add `GROQ_API_KEY` (Get a free key in 10s at [console.groq.com](https://console.groq.com)).
5. Click **Deploy**! 

Vercel will give you a public URL (e.g. `https://whisper-asr-api.vercel.app`) that works on phones, laptops, and classroom projectors!

---

## 📁 Repository Structure

```
whisper-asr-api/
├── index.html               # Main Web Studio interface (Vercel static root)
├── styles.css               # Clean presentation-ready stylesheet
├── app.js                   # Interactive player, sample library, subtitle generator
├── vercel.json              # Vercel deployment and routing configuration
├── api/
│   └── transcribe.js        # Vercel serverless function (Whisper API forwarder)
├── whisper_app_launcher.ipynb # 1-click Google Colab launcher
├── Dockerfile               # Production container image with FFmpeg
├── docker-compose.yml       # Docker compose orchestration
├── requirements.txt         # Python dependencies
├── app/                     # Python FastAPI Backend
│   ├── main.py              # FastAPI server entrypoint
│   ├── core/                # WhisperEngine, FFmpeg preprocessor, Exporters
│   ├── schemas/             # Pydantic v2 data models
│   └── api/v1/              # REST API endpoints (/transcribe, /evaluate, /health)
└── tests/
    └── test_api.py          # Automated test suite
```

---

## 💻 Local & Docker Execution (Optional)

If running the Python FastAPI server locally:

```bash
# 1. Install dependencies
pip install --prefer-binary -r requirements.txt

# 2. Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or with Docker:
```bash
docker compose up --build
```

---

## 📜 Academic Attribution

Developed at the **Indian Institute of Information Technology Allahabad (IIITA)** for the Multimedia Data Processing (MDP) Lab curriculum.  
Built on OpenAI Whisper, faster-whisper, and Vercel. Distributed under the MIT License.
