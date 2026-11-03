let selectedFile = null;
let currentResult = null;
let mediaRecorder = null;
let audioChunks = [];
let recordInterval = null;
let recordSeconds = 0;

// DOM Elements
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const fileChosenName = document.getElementById("file-chosen-name");
const tabUpload = document.getElementById("tab-upload");
const tabRecord = document.getElementById("tab-record");
const secUpload = document.getElementById("section-upload");
const secRecord = document.getElementById("section-record");
const btnRecord = document.getElementById("btn-record");
const recordTimer = document.getElementById("record-timer");
const audioPlayer = document.getElementById("audio-player");
const audioPreviewBox = document.getElementById("audio-preview-box");
const btnTranscribe = document.getElementById("btn-transcribe");
const transcribeBtnText = document.getElementById("transcribe-btn-text");
const transcribeSpinner = document.getElementById("transcribe-spinner");
const transcriptDisplay = document.getElementById("transcript-display");
const exportSection = document.getElementById("export-section");
const systemStatusText = document.getElementById("system-status-text");

// Metrics
const metricDuration = document.getElementById("metric-duration");
const metricLatency = document.getElementById("metric-latency");
const metricRtf = document.getElementById("metric-rtf");
const metricLang = document.getElementById("metric-lang");

// Evaluation
const refTextInput = document.getElementById("ref-text");
const btnEval = document.getElementById("btn-eval");
const evalScores = document.getElementById("eval-scores");

// Check Health on Load
async function checkHealth() {
  try {
    const res = await fetch("/api/v1/health");
    if (res.ok) {
      const data = await res.json();
      const dev = data.cuda_available ? (data.gpu_name ? data.gpu_name.split(" ")[0] : "CUDA") : "CPU";
      systemStatusText.textContent = `${data.current_model} (${dev})`;
    } else {
      systemStatusText.textContent = "Service Error";
    }
  } catch (e) {
    systemStatusText.textContent = "Offline";
  }
}
checkHealth();

// Tab Switchers
tabUpload.addEventListener("click", () => {
  tabUpload.classList.add("active");
  tabRecord.classList.remove("active");
  secUpload.classList.remove("hidden");
  secRecord.classList.add("hidden");
});

tabRecord.addEventListener("click", () => {
  tabRecord.classList.add("active");
  tabUpload.classList.remove("active");
  secRecord.classList.remove("hidden");
  secUpload.classList.add("hidden");
});

// Dropzone Events
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length > 0) {
    handleFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFile(e.target.files[0]);
  }
});

function handleFile(file) {
  selectedFile = file;
  fileChosenName.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
  const audioUrl = URL.createObjectURL(file);
  audioPlayer.src = audioUrl;
  audioPreviewBox.classList.remove("hidden");
  btnTranscribe.disabled = false;
}

// Microphone Recording
btnRecord.addEventListener("click", async () => {
  if (!mediaRecorder || mediaRecorder.state === "inactive") {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        selectedFile = new File([audioBlob], "microphone_recording.wav", { type: "audio/wav" });
        const audioUrl = URL.createObjectURL(audioBlob);
        audioPlayer.src = audioUrl;
        audioPreviewBox.classList.remove("hidden");
        btnTranscribe.disabled = false;
        fileChosenName.textContent = `Recorded: microphone_recording.wav (${(audioBlob.size / 1024).toFixed(1)} KB)`;
      };

      mediaRecorder.start();
      btnRecord.textContent = "⏹️ Stop Recording";
      btnRecord.style.backgroundColor = "var(--danger)";
      recordTimer.classList.remove("hidden");
      recordSeconds = 0;
      recordTimer.textContent = "00:00";
      recordInterval = setInterval(() => {
        recordSeconds++;
        const mins = String(Math.floor(recordSeconds / 60)).padStart(2, "0");
        const secs = String(recordSeconds % 60).padStart(2, "0");
        recordTimer.textContent = `${mins}:${secs}`;
      }, 1000);
    } catch (err) {
      alert("Microphone access denied or unsupported: " + err.message);
    }
  } else {
    mediaRecorder.stop();
    clearInterval(recordInterval);
    btnRecord.textContent = "🔴 Start Recording";
    btnRecord.style.backgroundColor = "var(--accent)";
  }
});

// Transcribe Submission
btnTranscribe.addEventListener("click", async () => {
  if (!selectedFile) return;

  btnTranscribe.disabled = true;
  transcribeBtnText.textContent = "Transcribing...";
  transcribeSpinner.classList.remove("hidden");
  transcriptDisplay.innerHTML = `<p style="color: var(--accent); text-align: center; margin-top: 3rem;">Processing audio through faster-whisper...</p>`;

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("model_size", document.getElementById("select-model").value);
  formData.append("language", document.getElementById("select-lang").value);
  formData.append("task", document.getElementById("select-task").value);
  formData.append("beam_size", document.getElementById("input-beam").value);
  formData.append("vad_filter", document.getElementById("chk-vad").checked);
  formData.append("word_timestamps", document.getElementById("chk-timestamps").checked);

  try {
    const response = await fetch("/api/v1/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Transcription request failed");
    }

    currentResult = await response.json();
    renderResults(currentResult);
  } catch (error) {
    transcriptDisplay.innerHTML = `<p style="color: var(--danger); padding: 1rem;">❌ Error: ${error.message}</p>`;
  } finally {
    btnTranscribe.disabled = false;
    transcribeBtnText.textContent = "Transcribe Audio";
    transcribeSpinner.classList.add("hidden");
  }
});

function renderResults(data) {
  const meta = data.metadata;
  metricDuration.textContent = `${meta.duration}s`;
  metricLatency.textContent = `${meta.processing_seconds}s`;
  metricRtf.textContent = meta.rtf;
  metricLang.textContent = `${meta.language ? meta.language.toUpperCase() : "N/A"} (${Math.round((meta.language_probability || 1) * 100)}%)`;

  if (!data.segments || data.segments.length === 0) {
    transcriptDisplay.innerHTML = `<p style="color: var(--text-muted); padding: 1rem;">[No speech recognized in the audio file]</p>`;
    exportSection.classList.add("hidden");
    return;
  }

  exportSection.classList.remove("hidden");

  let html = "";
  data.segments.forEach((seg, idx) => {
    html += `
      <div class="segment-item" id="seg-${idx}" onclick="jumpToTime(${seg.start})">
        <div class="segment-time">[${formatTimestamp(seg.start)} ➔ ${formatTimestamp(seg.end)}]</div>
        <div class="segment-text">${escapeHtml(seg.text)}</div>
      </div>
    `;
  });

  transcriptDisplay.innerHTML = html;
}

function jumpToTime(seconds) {
  audioPlayer.currentTime = seconds;
  audioPlayer.play();
}

// Synchronize audio playback highlight
audioPlayer.addEventListener("timeupdate", () => {
  if (!currentResult || !currentResult.segments) return;
  const current = audioPlayer.currentTime;
  currentResult.segments.forEach((seg, idx) => {
    const el = document.getElementById(`seg-${idx}`);
    if (el) {
      if (current >= seg.start && current <= seg.end) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    }
  });
});

function formatTimestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${String(ms).padStart(3, "0")}`;
}

function escapeHtml(text) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

// Download Handlers
function downloadCurrent(format) {
  if (!currentResult) return;
  const stem = selectedFile ? selectedFile.name.replace(/\.[^/.]+$/, "") : "transcript";

  if (format === "txt") {
    downloadBlob(currentResult.transcript + "\n", `${stem}.txt`, "text/plain");
  } else if (format === "json") {
    downloadBlob(JSON.stringify(currentResult, null, 2), `${stem}.json`, "application/json");
  } else if (format === "srt") {
    let srt = "";
    currentResult.segments.forEach((seg, i) => {
      srt += `${i + 1}\n${formatSrtTime(seg.start)} --> ${formatSrtTime(seg.end)}\n${seg.text}\n\n`;
    });
    downloadBlob(srt, `${stem}.srt`, "text/plain");
  } else if (format === "vtt") {
    let vtt = "WEBVTT\n\n";
    currentResult.segments.forEach((seg) => {
      vtt += `${formatVttTime(seg.start)} --> ${formatVttTime(seg.end)}\n${seg.text}\n\n`;
    });
    downloadBlob(vtt, `${stem}.vtt`, "text/vtt");
  }
}

function formatSrtTime(seconds) {
  const ms = Math.round(seconds * 1000);
  const hrs = Math.floor(ms / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  const remainMs = ms % 1000;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")},${String(remainMs).padStart(3, "0")}`;
}

function formatVttTime(seconds) {
  const ms = Math.round(seconds * 1000);
  const hrs = Math.floor(ms / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  const remainMs = ms % 1000;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${String(remainMs).padStart(3, "0")}`;
}

function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type: `${type};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Evaluation
btnEval.addEventListener("click", async () => {
  const refText = refTextInput.value.trim();
  if (!refText) {
    alert("Please enter a ground truth reference transcript.");
    return;
  }
  if (!currentResult || !currentResult.transcript) {
    alert("Please transcribe an audio recording first.");
    return;
  }

  evalScores.textContent = "Evaluating...";
  try {
    const res = await fetch("/api/v1/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reference_text: refText,
        hypothesis_text: currentResult.transcript,
      }),
    });
    if (!res.ok) throw new Error("Evaluation failed");
    const data = await res.json();
    evalScores.innerHTML = `WER: <span style="color:#38bdf8">${(data.wer * 100).toFixed(2)}%</span> | CER: <span style="color:#38bdf8">${(data.cer * 100).toFixed(2)}%</span>`;
  } catch (err) {
    evalScores.textContent = "Evaluation error: " + err.message;
  }
});
