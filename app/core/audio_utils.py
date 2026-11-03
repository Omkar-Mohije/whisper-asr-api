import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from app.config import settings

logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """Custom exception for audio conversion or validation errors."""
    pass


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg executable is available in PATH."""
    return shutil.which("ffmpeg") is not None


def preprocess_audio(
    input_path: Path,
    target_sr: int = 16000
) -> Tuple[np.ndarray, int, float, bool]:
    """
    Decodes and normalizes any audio/video input to 16 kHz mono float32.

    Returns:
        (audio_array, sample_rate, duration_seconds, is_silent)
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    # Generate isolated temporary path to prevent race conditions during concurrent requests
    temp_wav_path = settings.TEMP_DIR / f"norm_{uuid.uuid4().hex}.wav"

    try:
        if is_ffmpeg_available():
            command = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-vn",                 # ignore video streams
                "-ac", "1",            # force mono
                "-ar", str(target_sr), # force 16 kHz
                "-c:a", "pcm_s16le",
                str(temp_wav_path)
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                raise AudioProcessingError(f"FFmpeg decoding failed: {result.stderr[-500:]}")

            audio, sr = sf.read(str(temp_wav_path), dtype="float32")
        else:
            # Fallback for systems without FFmpeg using soundfile + scipy
            logger.warning("FFmpeg not found in PATH. Falling back to direct soundfile decoding.")
            try:
                audio, sr = sf.read(str(input_path), dtype="float32")
            except Exception as e:
                raise AudioProcessingError(
                    f"Unable to read audio without FFmpeg. Please install FFmpeg for broad audio/video support: {e}"
                )

            # Convert multi-channel (stereo) to mono
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            # Resample to 16000 Hz if needed
            if sr != target_sr:
                # Use rational resampling
                from math import gcd
                common = gcd(target_sr, sr)
                up = target_sr // common
                down = sr // common
                audio = resample_poly(audio, up, down).astype(np.float32)
                sr = target_sr

        # Waveform integrity validation
        if audio.ndim != 1:
            raise AudioProcessingError(f"Expected 1D mono audio array, got shape {audio.shape}")

        if audio.size == 0:
            raise AudioProcessingError("The provided audio file contains no audible samples.")

        if not np.isfinite(audio).all():
            raise AudioProcessingError("Audio waveform contains invalid NaN or infinite samples.")

        duration = float(len(audio) / sr)

        # Check for silence gracefully instead of crashing
        max_amplitude = float(np.max(np.abs(audio)))
        is_silent = max_amplitude < 1e-5

        return audio, sr, duration, is_silent

    finally:
        if temp_wav_path.exists():
            try:
                temp_wav_path.unlink()
            except OSError:
                pass
