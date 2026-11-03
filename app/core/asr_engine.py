import ctypes
import glob
import logging
import os
import threading
import time
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


def _setup_cuda_libraries():
    """Auto-detect and preload pip-installed NVIDIA CUDA/cuBLAS/cuDNN shared libraries on Linux/Colab."""
    try:
        import site
        search_dirs = []
        for p in site.getsitepackages():
            search_dirs.extend(glob.glob(f"{p}/nvidia/*/lib"))

        if search_dirs:
            existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(search_dirs) + (":" + existing_ld if existing_ld else "")

            # Explicitly preload libcublas and dependencies using RTLD_GLOBAL
            for d in search_dirs:
                for so in ("libcublas.so.12", "libcublasLt.so.12", "libcudnn.so.9", "libcudnn.so.8"):
                    so_path = os.path.join(d, so)
                    if os.path.isfile(so_path):
                        try:
                            ctypes.CDLL(so_path, mode=ctypes.RTLD_GLOBAL)
                        except Exception:
                            pass
    except Exception as e:
        logger.debug("CUDA library auto-link check completed: %s", e)


class WhisperEngine:
    """
    Thread-safe Singleton inference engine managing faster-whisper model lifecycle,
    caching, and transcription execution.
    """
    _instance: Optional["WhisperEngine"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "WhisperEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._model = None
        self._current_model_size: Optional[str] = None
        self._current_device: Optional[str] = None
        self._current_compute_type: Optional[str] = None
        self._infer_lock = threading.Lock()
        self._initialized = True

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_info(self) -> Dict[str, Any]:
        return {
            "model_size": self._current_model_size,
            "device": self._current_device,
            "compute_type": self._current_compute_type,
            "is_loaded": self.is_loaded,
        }

    def load_model(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None
    ) -> None:
        """Loads or reloads the faster-whisper model."""
        target_model = model_size or settings.WHISPER_MODEL_SIZE

        resolved_dev, resolved_comp = settings.resolve_device_and_compute()
        target_device = device if (device and device != "auto") else resolved_dev
        target_compute = compute_type if (compute_type and compute_type != "auto") else resolved_comp

        if (
            self._model is not None
            and self._current_model_size == target_model
            and self._current_device == target_device
            and self._current_compute_type == target_compute
        ):
            logger.info("Using currently loaded Whisper model: %s (%s, %s)", target_model, target_device, target_compute)
            return

        with self._lock:
            _setup_cuda_libraries()
            from faster_whisper import WhisperModel

            logger.info(
                "Loading faster-whisper model '%s' on device '%s' with compute_type '%s' ...",
                target_model, target_device, target_compute
            )
            start_time = time.time()

            kwargs: Dict[str, Any] = {
                "model_size_or_path": target_model,
                "device": target_device,
                "compute_type": target_compute,
            }
            if target_device == "cpu" and settings.WHISPER_CPU_THREADS > 0:
                kwargs["cpu_threads"] = settings.WHISPER_CPU_THREADS

            try:
                self._model = WhisperModel(**kwargs)
                self._current_model_size = target_model
                self._current_device = target_device
                self._current_compute_type = target_compute
            except Exception as e:
                if target_device == "cuda":
                    logger.warning("CUDA execution failed (%s). Falling back safely to CPU (int8)...", e)
                    kwargs["device"] = "cpu"
                    kwargs["compute_type"] = "int8"
                    if settings.WHISPER_CPU_THREADS > 0:
                        kwargs["cpu_threads"] = settings.WHISPER_CPU_THREADS
                    self._model = WhisperModel(**kwargs)
                    self._current_model_size = target_model
                    self._current_device = "cpu"
                    self._current_compute_type = "int8"
                else:
                    raise e

            logger.info("Model loaded successfully in %.2f seconds on %s.", time.time() - start_time, self._current_device)

    def transcribe(
        self,
        audio_array: np.ndarray,
        duration: float,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: Optional[int] = None,
        vad_filter: Optional[bool] = None,
        min_silence_duration_ms: Optional[int] = None,
        speech_pad_ms: Optional[int] = None,
        word_timestamps: bool = True,
        condition_on_previous_text: bool = True,
        is_silent: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes robust speech recognition on normalized 16kHz audio array.
        Handles missing timestamps, silent audio, and VAD parameters gracefully.
        """
        if not self.is_loaded:
            self.load_model()

        # If audio is detected as completely silent, return an empty result immediately
        if is_silent:
            logger.info("Audio marked as silent; bypassing inference.")
            return {
                "metadata": {
                    "language": language or "en",
                    "language_probability": 1.0,
                    "duration": round(duration, 2),
                    "processing_seconds": 0.001,
                    "rtf": 0.0,
                    "model_size": self._current_model_size,
                    "device": self._current_device,
                    "compute_type": self._current_compute_type,
                },
                "transcript": "",
                "segments": []
            }

        beam = beam_size if beam_size is not None else settings.DEFAULT_BEAM_SIZE
        vad = vad_filter if vad_filter is not None else settings.DEFAULT_VAD_FILTER
        silence_ms = (
            min_silence_duration_ms
            if min_silence_duration_ms is not None
            else settings.DEFAULT_MIN_SILENCE_DURATION_MS
        )
        pad_ms = speech_pad_ms if speech_pad_ms is not None else settings.DEFAULT_SPEECH_PAD_MS

        start_time = time.time()

        with self._infer_lock:
            try:
                segments_generator, info = self._model.transcribe(
                    audio_array,
                    language=language if language else None,
                    task=task,
                    beam_size=beam,
                    vad_filter=vad,
                    vad_parameters={
                        "min_silence_duration_ms": silence_ms,
                        "speech_pad_ms": pad_ms,
                    },
                    word_timestamps=word_timestamps,
                    condition_on_previous_text=condition_on_previous_text,
                )
                segments = self._consume_segments(segments_generator, word_timestamps)
            except Exception as infer_err:
                if self._current_device == "cuda":
                    logger.warning("GPU transcription failed (%s). Retrying seamlessly on CPU...", infer_err)
                    self.load_model(device="cpu", compute_type="int8")
                    segments_generator, info = self._model.transcribe(
                        audio_array,
                        language=language if language else None,
                        task=task,
                        beam_size=beam,
                        vad_filter=vad,
                        vad_parameters={
                            "min_silence_duration_ms": silence_ms,
                            "speech_pad_ms": pad_ms,
                        },
                        word_timestamps=word_timestamps,
                        condition_on_previous_text=condition_on_previous_text,
                    )
                    segments = self._consume_segments(segments_generator, word_timestamps)
                else:
                    raise infer_err

        elapsed = time.time() - start_time
        rtf = round(elapsed / duration, 4) if duration > 0 else 0.0

        lang_prob = float(info.language_probability) if getattr(info, "language_probability", None) is not None else 0.0
        full_transcript = " ".join(s["text"] for s in segments if s["text"]).strip()

        return {
            "metadata": {
                "language": info.language,
                "language_probability": round(lang_prob, 4),
                "duration": round(duration, 2),
                "processing_seconds": round(elapsed, 3),
                "rtf": rtf,
                "model_size": self._current_model_size,
                "device": self._current_device,
                "compute_type": self._current_compute_type,
            },
            "transcript": full_transcript,
            "segments": segments,
        }

    def _consume_segments(self, segments_generator, word_timestamps: bool) -> List[Dict[str, Any]]:
        segments: List[Dict[str, Any]] = []
        for seg in segments_generator:
            words: List[Dict[str, Any]] = []
            if word_timestamps and getattr(seg, "words", None):
                for word in seg.words:
                    w_start = float(word.start) if word.start is not None else None
                    w_end = float(word.end) if word.end is not None else None
                    w_prob = float(word.probability) if getattr(word, "probability", None) is not None else None
                    words.append({
                        "start": w_start,
                        "end": w_end,
                        "word": word.word,
                        "probability": w_prob,
                    })

            seg_start = float(seg.start) if seg.start is not None else 0.0
            seg_end = float(seg.end) if seg.end is not None else seg_start
            seg_text = seg.text.strip() if seg.text else ""

            avg_logprob = float(seg.avg_logprob) if getattr(seg, "avg_logprob", None) is not None else None
            no_speech_prob = float(seg.no_speech_prob) if getattr(seg, "no_speech_prob", None) is not None else None

            segments.append({
                "id": len(segments),
                "start": round(seg_start, 3),
                "end": round(seg_end, 3),
                "text": seg_text,
                "avg_logprob": avg_logprob,
                "no_speech_prob": no_speech_prob,
                "words": words,
            })
        return segments


_engine = WhisperEngine()


def get_whisper_engine() -> WhisperEngine:
    return _engine
