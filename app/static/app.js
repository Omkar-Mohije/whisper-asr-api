// Whisper ASR Studio — Interactive Client Logic

let activeFile = null;
let currentTranscriptData = null;
let mediaRecorder = null;
let audioChunks = [];
let recordTimerInterval = null;
let recordSeconds = 0;

// DOM Elements
const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const selectedFileInfo = document.getElementById("selected-file-info");
const btnRecord = document.getElementById("btn-record");
const btnStopRecord = document.getElementById("btn-stop-record");
const recordingStatus = document.getElementById("recording-status");
const recordTimer = document.getElementById("record-timer");
const btnTranscribe = document.getElementById("btn-primary-main") || document.getElementById("btn-transcribe");
const transcribeText = document.getElementById("transcribe-text");
const spinner = document.getElementById("spinner");

const playerContainer = document.getElementById("player-container");
const audioPlayer = document.getElementById("audio-player");
const resultsCard = document.getElementById("results-card");
const segmentsContainer = document.getElementById("segments-container");

const metricDuration = document.getElementById("metric-duration");
const metricLatency = document.getElementById("metric-latency");
const metricRtf = document.getElementById("metric-rtf");
const metricLang = document.getElementById("metric-lang");

const modalSettings = document.getElementById("modal-settings");
const apiKeyInput = document.getElementById("api-key-input");
const refInput = document.getElementById("ref-input");
const evalResult = document.getElementById("eval-result");

// Load stored API key
const savedApiKey = localStorage.getItem("groq_api_key") || "";
if (apiKeyInput) apiKeyInput.value = savedApiKey;

// Settings Modal Controls
document.getElementById("btn-settings-toggle").addEventListener("click", () => {
  modalSettings.classList.remove("hidden");
});

function closeSettings() {
  modalSettings.classList.add("hidden");
}

function saveSettings() {
  const key = apiKeyInput.value.trim();
  if (key) {
    localStorage.setItem("groq_api_key", key);
    alert("API Key saved securely in your browser!");
  } else {
    localStorage.removeItem("groq_api_key");
  }
  closeSettings();
}

// Drag & Drop
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.style.borderColor = "#2563eb";
});

dropzone.addEventListener("dragleave", () => {
  dropzone.style.borderColor = "#93c5fd";
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.style.borderColor = "#93c5fd";
  if (e.dataTransfer.files.length > 0) {
    handleFileSelected(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

function handleFileSelected(file) {
  activeFile = file;
  selectedFileInfo.classList.remove("hidden");
  selectedFileInfo.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;

  const fileUrl = URL.createObjectURL(file);
  audioPlayer.src = fileUrl;
  playerContainer.classList.remove("hidden");
  btnTranscribe.disabled = false;
}

// Microphone Recording
btnRecord.addEventListener("click", async () => {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Microphone recording is not supported in this browser.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      activeFile = new File([audioBlob], "recorded_speech.wav", { type: "audio/wav" });
      const audioUrl = URL.createObjectURL(audioBlob);
      audioPlayer.src = audioUrl;
      playerContainer.classList.remove("hidden");
      btnTranscribe.disabled = false;
      selectedFileInfo.classList.remove("hidden");
      selectedFileInfo.textContent = `Recorded: recorded_speech.wav (${(audioBlob.size / 1024).toFixed(1)} KB)`;
    };

    mediaRecorder.start();
    recordingStatus.classList.remove("hidden");
    btnRecord.classList.add("hidden");
    recordSeconds = 0;
    recordTimer.textContent = "00:00";
    recordTimerInterval = setInterval(() => {
      recordSeconds++;
      const m = String(Math.floor(recordSeconds / 60)).padStart(2, "0");
      const s = String(recordSeconds % 60).padStart(2, "0");
      recordTimer.textContent = `${m}:${s}`;
    }, 1000);
  } catch (err) {
    alert("Microphone access error: " + err.message);
  }
});

btnStopRecord.addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    clearInterval(recordTimerInterval);
    recordingStatus.classList.add("hidden");
    btnRecord.classList.remove("hidden");
  }
});

// Built-in Demo Samples (Modeled after Apna Babu's instant samples!)
const SAMPLE_LIBRARY = {
  lecture: {
    title: "College Lecture (Hinglish)",
    duration: 24.5,
    language: "Hinglish (hi/en)",
    segments: [
      { id: 0, start: 0.0, end: 4.8, text: "Good morning everyone. Aaj hum speech recognition pipeline and Whisper architecture discuss karenge." },
      { id: 1, start: 5.0, end: 11.2, text: "Basically, audio waveform ko 16 kHz mono me resample kiya jata hai, followed by Voice Activity Detection." },
      { id: 2, start: 11.5, end: 17.6, text: "Whisper large-v3-turbo encoder-decoder transformer use karta hai token prediction and timestamp alignment ke liye." },
      { id: 3, start: 18.0, end: 24.5, text: "Iss process se humein high accuracy subtitles, word-level timings, aur language translation milta hai." }
    ]
  },
  announcement: {
    title: "Official Notice (Hindi)",
    duration: 18.2,
    language: "Hindi (hi)",
    segments: [
      { id: 0, start: 0.0, end: 5.2, text: "सभी विद्यार्थियों को सूचित किया जाता है कि सेमेस्टर परीक्षा फॉर्म भरने की अंतिम तिथि 15 नवंबर है।" },
      { id: 1, start: 5.5, end: 11.8, text: "कृपया संस्थान के छात्र पोर्टल पर जाकर अपने विषय कोड और शुल्क रसीद का सत्यापन अवश्य कर लें।" },
      { id: 2, start: 12.0, end: 18.2, text: "किसी भी विसंगति की स्थिति में शैक्षणिक विभाग के कार्यालय में संपर्क करें। धन्यवाद।" }
    ]
  },
  voicenote: {
    title: "Quick Voice Memo (English)",
    duration: 14.0,
    language: "English (en)",
    segments: [
      { id: 0, start: 0.0, end: 4.5, text: "Hey team, I just pushed the new ASR API repository and Vercel configuration." },
      { id: 1, start: 4.8, end: 9.3, text: "Make sure to test the subtitle exports and synchronized cue player on your phone." },
      { id: 2, start: 9.6, end: 14.0, text: "We are ready for the presentation today. Good luck everyone!" }
    ]
  }
};

function generateSampleAudio(durationSec) {
  // Generates pleasant synthesized audio tone using browser Web Audio API
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const sampleRate = ctx.sampleRate;
  const numFrames = sampleRate * durationSec;
  const audioBuffer = ctx.createBuffer(1, numFrames, sampleRate);
  const channelData = audioBuffer.getChannelData(0);

  for (let i = 0; i < numFrames; i++) {
    const t = i / sampleRate;
    // Layered harmonic chords for a clean chime
    channelData[i] = (
      Math.sin(2 * Math.PI * 220 * t) * 0.15 +
      Math.sin(2 * Math.PI * 330 * t) * 0.1 +
      Math.sin(2 * Math.PI * 440 * t) * 0.05
    ) * Math.exp(-0.8 * (t % 3));
  }

  // Convert buffer to WAV Blob
  return bufferToWave(audioBuffer, numFrames);
}

function bufferToWave(abuffer, len) {
  let numOfChan = abuffer.numberOfChannels,
      length = len * numOfChan * 2 + 44,
      out = new DataView(new ArrayBuffer(length)),
      channels = [], i, sample,
      offset = 0,
      pos = 0;

  function setUint16(data) { out.setUint16(pos, data, true); pos += 2; }
  function setUint32(data) { out.setUint32(pos, data, true); pos += 4; }

  setUint32(0x46464952); // "RIFF"
  setUint32(length - 8);
  setUint32(0x45564157); // "WAVE"
  setUint32(0x20746d66); // "fmt "
  setUint32(16);
  setUint16(1);
  setUint16(numOfChan);
  setUint32(abuffer.sampleRate);
  setUint32(abuffer.sampleRate * 2 * numOfChan);
  setUint16(numOfChan * 2);
  setUint16(16);
  setUint32(0x61746164); // "data"
  setUint32(length - pos - 4);

  for (i = 0; i < abuffer.numberOfChannels; i++)
    channels.push(abuffer.getChannelData(i));

  while (offset < len) {
    for (i = 0; i < numOfChan; i++) {
      sample = Math.max(-1, Math.min(1, channels[i][offset]));
      sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
      out.setInt16(pos, sample, true);
      pos += 2;
    }
    offset++;
  }
  return new Blob([out], { type: "audio/wav" });
}

function loadSample(key) {
  const sample = SAMPLE_LIBRARY[key];
  if (!sample) return;

  const audioBlob = generateSampleAudio(sample.duration);
  const audioUrl = URL.createObjectURL(audioBlob);
  audioPlayer.src = audioUrl;
  playerContainer.classList.remove("hidden");

  selectedFileInfo.classList.remove("hidden");
  selectedFileInfo.textContent = `Loaded Sample: ${sample.title}`;

  // Form structured result
  const transcriptText = sample.segments.map(s => s.text).join(" ");
  currentTranscriptData = {
    transcript: transcriptText,
    segments: sample.segments,
    metadata: {
      duration: sample.duration,
      processing_seconds: 0.38,
      rtf: (0.38 / sample.duration).toFixed(3),
      language: sample.language
    }
  };

  renderResults(currentTranscriptData);
}

// Transcribe Submission
btnTranscribe.addEventListener("click", async () => {
  if (!activeFile) return;

  btnTranscribe.disabled = true;
  transcribeText.textContent = "Transcribing with Whisper Large-v3-Turbo...";
  spinner.classList.remove("hidden");

  const apiKey = localStorage.getItem("groq_api_key") || "";
  const task = document.getElementById("opt-task").value;
  const language = document.getElementById("opt-language").value;

  const formData = new FormData();
  formData.append("file", activeFile);
  formData.append("model", "whisper-large-v3-turbo");
  formData.append("response_format", "verbose_json");
  if (language) formData.append("language", language);

  const startTime = Date.now();

  try {
    let response;
    // 1. Try local / Cloudflare FastAPI backend
    try {
      response = await fetch("/api/v1/transcribe", {
        method: "POST",
        body: formData,
      });
    } catch (netErr) {
      if (apiKey) {
        response = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
          method: "POST",
          headers: { "Authorization": `Bearer ${apiKey}` },
          body: formData,
        });
      } else {
        throw netErr;
      }
    }

    if (!response.ok) {
      // If FastAPI failed or was 404, fallback to Groq if key exists
      if (apiKey) {
        response = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
          method: "POST",
          headers: { "Authorization": `Bearer ${apiKey}` },
          body: formData,
        });
      }
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error?.message || err.detail || "Transcription failed.");
      }
    }

    const data = await response.json();
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);

    if (data.segments && data.metadata && data.transcript !== undefined) {
      currentTranscriptData = {
        transcript: data.transcript,
        segments: data.segments,
        metadata: data.metadata
      };
    } else {
      const dur = data.duration || 10.0;
      const segments = (data.segments || []).map((s, idx) => ({
        id: idx,
        start: s.start || 0.0,
        end: s.end || 0.0,
        text: s.text.trim()
      }));

      currentTranscriptData = {
        transcript: data.text || "",
        segments: segments,
        metadata: {
          duration: dur,
          processing_seconds: elapsed,
          rtf: (elapsed / dur).toFixed(3),
          language: data.language ? data.language.toUpperCase() : "Detected"
        }
      };
    }

    renderResults(currentTranscriptData);

  } catch (error) {
    alert("Notice: " + error.message + "\n\nTip: You can get an instant free Groq API key at console.groq.com to transcribe any custom file, or click one of the 3 built-in samples above to test immediately!");
  } finally {
    btnTranscribe.disabled = false;
    transcribeText.textContent = "⚡ Transcribe with Whisper Large-v3-Turbo";
    spinner.classList.add("hidden");
  }
});

function renderResults(data) {
  resultsCard.classList.remove("hidden");
  const meta = data.metadata;

  metricDuration.textContent = `${meta.duration}s`;
  metricLatency.textContent = `${meta.processing_seconds}s`;
  metricRtf.textContent = meta.rtf;
  metricLang.textContent = meta.language;

  let html = "";
  data.segments.forEach((seg, i) => {
    html += `
      <div class="cue-segment" id="cue-${i}" onclick="seekTo(${seg.start})">
        <div class="cue-time">[${formatCueTime(seg.start)} &rarr; ${formatCueTime(seg.end)}]</div>
        <div class="cue-text">${escapeHtml(seg.text)}</div>
      </div>
    `;
  });

  segmentsContainer.innerHTML = html;
  resultsCard.scrollIntoView({ behavior: "smooth" });
}

function seekTo(seconds) {
  audioPlayer.currentTime = seconds;
  audioPlayer.play();
}

// Synchronized audio cue player
audioPlayer.addEventListener("timeupdate", () => {
  if (!currentTranscriptData || !currentTranscriptData.segments) return;
  const cur = audioPlayer.currentTime;
  currentTranscriptData.segments.forEach((seg, idx) => {
    const el = document.getElementById(`cue-${idx}`);
    if (el) {
      if (cur >= seg.start && cur <= seg.end) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    }
  });
});

function formatCueTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(ms).padStart(3, "0")}`;
}

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

function copyTranscript() {
  if (!currentTranscriptData) return;
  navigator.clipboard.writeText(currentTranscriptData.transcript);
  alert("Transcript copied to clipboard!");
}

// Exports
function exportData(format) {
  if (!currentTranscriptData) return;
  const stem = "whisper_transcript";

  if (format === "txt") {
    downloadBlob(currentTranscriptData.transcript + "\n", `${stem}.txt`, "text/plain");
  } else if (format === "json") {
    downloadBlob(JSON.stringify(currentTranscriptData, null, 2), `${stem}.json`, "application/json");
  } else if (format === "srt") {
    let srt = "";
    currentTranscriptData.segments.forEach((seg, i) => {
      srt += `${i + 1}\n${formatSrt(seg.start)} --> ${formatSrt(seg.end)}\n${seg.text}\n\n`;
    });
    downloadBlob(srt, `${stem}.srt`, "text/plain");
  } else if (format === "vtt") {
    let vtt = "WEBVTT\n\n";
    currentTranscriptData.segments.forEach((seg) => {
      vtt += `${formatVtt(seg.start)} --> ${formatVtt(seg.end)}\n${seg.text}\n\n`;
    });
    downloadBlob(vtt, `${stem}.vtt`, "text/vtt");
  }
}

function formatSrt(s) {
  const ms = Math.round(s * 1000);
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const sec = Math.floor((ms % 60000) / 1000);
  const remain = ms % 1000;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")},${String(remain).padStart(3, "0")}`;
}

function formatVtt(s) {
  const ms = Math.round(s * 1000);
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const sec = Math.floor((ms % 60000) / 1000);
  const remain = ms % 1000;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}.${String(remain).padStart(3, "0")}`;
}

function downloadBlob(content, name, type) {
  const blob = new Blob([content], { type: `${type};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Client-side WER/CER calculation
function calculateWER() {
  const ref = refInput.value.trim().toLowerCase();
  if (!ref) {
    alert("Please enter a ground truth reference transcript.");
    return;
  }
  if (!currentTranscriptData || !currentTranscriptData.transcript) {
    alert("Please transcribe an audio first.");
    return;
  }

  const hyp = currentTranscriptData.transcript.toLowerCase();
  const wer = levenshteinWords(ref, hyp);
  evalResult.innerHTML = `WER: <span style="color:#2563eb">${(wer * 100).toFixed(1)}%</span>`;
}

function levenshteinWords(ref, hyp) {
  const rWords = ref.split(/\s+/).filter(Boolean);
  const hWords = hyp.split(/\s+/).filter(Boolean);
  if (rWords.length === 0) return 0.0;

  const d = Array(rWords.length + 1).fill(null).map(() => Array(hWords.length + 1).fill(0));
  for (let i = 0; i <= rWords.length; i++) d[i][0] = i;
  for (let j = 0; j <= hWords.length; j++) d[0][j] = j;

  for (let i = 1; i <= rWords.length; i++) {
    for (let j = 1; j <= hWords.length; j++) {
      const cost = rWords[i - 1] === hWords[j - 1] ? 0 : 1;
      d[i][j] = Math.min(
        d[i - 1][j] + 1,
        d[i][j - 1] + 1,
        d[i - 1][j - 1] + cost
      );
    }
  }
  return d[rWords.length][hWords.length] / rWords.length;
}
